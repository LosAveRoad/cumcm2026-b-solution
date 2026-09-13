function run_one_figure(n)
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai';
switch n
case 1;run([base '/figures/draw_framework.m']);
case 2;run([base '/figures/draw_eda_radii.m']);
case 3;run([base '/figures/draw_eda_constraint_line.m']);
case 4;run([base '/figures/draw_eda_time_components.m']);
case 5;run([base '/figures/draw_eda_protocol_ranges.m']);
case 6;run([base '/figures/draw_halfplane.m']);
case 7;run([base '/figures/draw_wedge_intersect.m']);
case 8;run([base '/figures/draw_jung_vs_diamond.m']);
case 9;run([base '/figures/draw_q1_example_polygon.m']);
case 10;run([base '/figures/draw_q1_mc_diameter.m']);
case 11;run([base '/figures/draw_q1_jung_ratio_area.m']);
case 12;run([base '/figures/draw_second_station.m']);
case 15;run([base '/figures/draw_q2_sensitivity.m']);
case 16;run([base '/figures/draw_q2_err_sweep.m']);
case 17;run([base '/figures/draw_q3_nine_disk.m']);
case 18;run([base '/figures/draw_q34_scout_nets.m']);
case 20;run([base '/figures/draw_directional_listen.m']);
case 21;run([base '/figures/draw_q4_directional_sector.m']);
case 22;run([base '/figures/draw_q4_silent_spoke.m']);
case 23;run([base '/figures/draw_q4_sector_chase.m']);
case 24;run([base '/figures/draw_q4_optical_grid.m']);
case 25;run([base '/figures/draw_q4_fullclear_bars.m']);
case 26;run([base '/figures/draw_q4_rehearsal_bars.m']);
case 27;run([base '/figures/draw_q4_ring_ablation.m']);
otherwise;error('Skipped: missing original data');
end
end
