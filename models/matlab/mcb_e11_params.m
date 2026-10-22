%% e11 simulation parameters (single source of truth)
%
% Edit this file to change the scenario. Everything else is derived.
%
% NOTE ON STOP TIME
%   The e11 rotor inertia is 0.030 kg*m2 (Motor-CAD measured). Spinning up
%   from standstill to 3000 rpm takes roughly 1 s, so a 0.5 s window stops
%   mid-transient (it reports ~2150 rpm and looks like a controller fault).
%   Use >= 1.5 s whenever the scenario starts from rest.

%% ==== User-adjustable scenario =====================================
SCEN.speed_ref_rpm   = 3000;     % Target mechanical speed [rpm]
SCEN.load_torque_nm  = 0;        % Load torque [Nm], positive = motoring
SCEN.stop_time_s     = 2.0;      % Simulation stop time [s]
SCEN.solver          = 'ode23tb';
SCEN.max_step_s      = 1e-4;

%% ==== Fixed electrical setup ======================================
ELEC.pwm_hz          = 20e3;
ELEC.vdc             = 400;      % DC bus [V]

%% ==== Derived ======================================================
ELEC.T_pwm = 1/ELEC.pwm_hz;
Ts         = ELEC.T_pwm;
Ts_speed   = 30*Ts;
Ts_simulink = ELEC.T_pwm/2;
Ts_motor    = ELEC.T_pwm/2;
Ts_inverter = ELEC.T_pwm/2;
dataType    = 'single';

fprintf('=== Scenario (from mcb_e11_params.m) ===\n');
fprintf('  speed ref  = %d rpm\n', SCEN.speed_ref_rpm);
fprintf('  load torque= %d Nm\n', SCEN.load_torque_nm);
fprintf('  stop time  = %.2f s\n', SCEN.stop_time_s);
fprintf('  solver     = %s, max step %.1e s\n', SCEN.solver, SCEN.max_step_s);
