import itertools
import math
import time
import unittest
from fractions import Fraction
from certificates import certified_covered
from offline_validation import OfflineClient, make_scene, validate_scene
from searcher import Searcher, contraction_step, q3_scouts, tsp_visit_order


class Q3Tests(unittest.TestCase):
    def test_hexagon_slack_counterexamples(self):
        for extra in (5e-7, 5e-10):
            a = 1000+extra
            sites = [(a*math.cos(k*math.pi/3), a*math.sin(k*math.pi/3)) for k in range(6)]
            self.assertFalse(certified_covered(sites, [((0, 0), 1000)]))

    def test_exact_boundary_and_nearby_distinct_centers(self):
        self.assertTrue(certified_covered([(0, 0)], [((0, 0), 1000)]))
        self.assertFalse(certified_covered([(5e-10, 0)], [((0, 0), 1000)]))
        self.assertTrue(certified_covered([(0, 0)], [((0, 0), 0)]))

    def test_empty_and_budget_unknown(self):
        self.assertFalse(certified_covered([], [((0, 0), 1000)]))
        self.assertFalse(certified_covered(q3_scouts(), [((0, 0), 1800)], max_boxes=0))
        self.assertTrue(certified_covered(q3_scouts(), [((0, 0), 1800)], max_boxes=8192))

    def test_partial_rejected_scan_never_commits(self):
        dog = Searcher(OfflineClient(make_scene(1, 10, "regression"), reject_measure=5))
        result = dog.run()
        self.assertFalse(result["complete"])
        self.assertEqual(result["reason"], "measure_rejected")
        self.assertEqual(dog.discovery_stations, [])

    def test_budget_and_deadline_never_claim_success(self):
        dog = Searcher(OfflineClient(make_scene(1, 10, "regression")), max_actions=5)
        result = dog.run()
        self.assertFalse(result["complete"])
        self.assertEqual(result["n_actions"], 5)
        self.assertEqual(dog.discovery_stations, [])
        self.assertEqual(result["reason"], "action_budget")
        dog = Searcher(OfflineClient(make_scene(1, 10, "regression"), duration=0))
        self.assertEqual(dog.run()["reason"], "runtime_deadline")

    def test_contraction_all_ranges_and_error_endpoints(self):
        for bound in (1500, 751.5, 100, 23.8):
            p, next_bound = contraction_step((0, 0), 0, bound)
            for i in range(101):
                r = bound*i/100
                for error in (-1, 0, 1):
                    a = math.radians(error)
                    self.assertLessEqual(math.dist(p, (r*math.cos(a), r*math.sin(a))), next_bound)
        r = 1500
        for _ in range(7):
            _, r = contraction_step((0, 0), 0, r)
        self.assertLess(r, 12)

    def test_nearest_not_first(self):
        source = (1400, 0)
        self.assertLess(min(math.dist(source, s) for s in q3_scouts()), 956.052)
        self.assertGreater(2*1400*math.sin(math.radians(.5)), 20)

    def test_tsp_against_exhaustive(self):
        origin, points = (4, -1), [(0, 0), (3, 7), (-4, 5), (10, 4)]
        def cost(order):
            path = [origin]+[points[i] for i in order]
            return sum(math.dist(a, b) for a, b in zip(path, path[1:]))
        self.assertAlmostEqual(cost(tsp_visit_order(origin, points)),
                               min(map(cost, itertools.permutations(range(4)))))

    def test_full_run_without_optional_pruning(self):
        validate_scene(81, 16, "boundary", "extremes", prune=False)

    def test_failed_certificate_is_not_success(self):
        class Broken(OfflineClient):
            def clear(self, rid, x, y, channel):
                return {"accepted": True, "clear_result": "no_target_in_range"}
        dog = Searcher(Broken(make_scene(1, 10, "regression")))
        self.assertEqual(dog.run()["reason"], "certified_clear_failed")

    def test_invalid_enter_duration_still_exits(self):
        class Broken(OfflineClient):
            def enter(self, rid):
                return self._response(rid)
        dog = Searcher(Broken({}))
        result = dog.run()
        self.assertEqual(result["reason"], "invalid_remaining_duration")
        self.assertEqual(dog.trace[-1]["path"], "/exit")

    def test_exit_rejection_is_reported(self):
        class Broken(OfflineClient):
            def exit(self, rid):
                return {"accepted": False}
        dog = Searcher(Broken(make_scene(2, 10, "regression")))
        result = dog.run()
        self.assertFalse(result["complete"])
        self.assertTrue(result["reason"].startswith("exit_exception:"))

    def test_http_payload_contract_without_network(self):
        import json
        from sim_client import SimClient
        captured = []
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"accepted":true}'
        def opener(request, timeout):
            captured.append((request.full_url, json.loads(request.data)))
            return Response()
        client = SimClient(robot_id="test-team", opener=opener)
        client.measure("test-rid", 1.5, -2, 20)
        url, body = captured[0]
        self.assertEqual(url, "http://127.0.0.1:2026/measure")
        self.assertEqual(body["position"], {"x": 1.5, "y": -2.0})
        self.assertEqual(body["channel"], 20)
        self.assertEqual(body["request_id"], "test-rid")
        self.assertEqual(body["arena_id"], "default")


if __name__ == "__main__":
    unittest.main(verbosity=2)
