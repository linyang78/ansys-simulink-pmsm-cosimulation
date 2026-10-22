%% e11 PMSM setup for mcb_pmsm_nonlin_fwc (non-linear LUT workflow)
%
% Data sources:
%   - Motor-CAD ECE 91x91 map  -> Ld/Lq/FluxPM tables (secant method)
%   - Motor-CAD measurement    -> J = 0.030023 kg.m2, friction 30 W @ 6000 rpm
%   - LUT validated against Motor-CAD CSV at 6000 rpm: Ld +2.6%, Lq +0.6%
%
% The full PMSMLUT (incl. id/iq reference tables) is prebuilt in
%   models/matlab/e11_pmsmlut_full.mat
% Regenerate it with python/.thincoder tooling if the ECE data changes.

clear; clc;

root = 'E:\Vscode\thincoder-pmsm';
addpath(fullfile(root, 'models', 'matlab'));

%% Simulation timing
PWM_frequency = 20e3;
T_pwm = 1/PWM_frequency;
Ts = T_pwm;
Ts_simulink = T_pwm/2;
Ts_motor = T_pwm/2;
Ts_inverter = T_pwm/2;
Ts_speed = 30*Ts;

dataType = 'single';

%% Load prebuilt motor + LUT
S = load(fullfile(root, 'models', 'matlab', 'e11_pmsmlut_full.mat'));
pmsm = S.pmsm;
inverter = S.inverter;
PMSMLUT = S.PMSMLUT;

fprintf('=== e11 motor ===\n');
fprintf('  p        = %d\n', pmsm.p);
fprintf('  Rs       = %.6f ohm\n', pmsm.Rs);
fprintf('  Ld       = %.1f uH (rated point)\n', pmsm.Ld*1e6);
fprintf('  Lq       = %.1f uH (rated point)\n', pmsm.Lq*1e6);
fprintf('  J        = %.6f kg.m2\n', pmsm.J);
fprintf('  B        = %.3e kg.m2/s\n', pmsm.B);
fprintf('  FluxPM   = %.6f Wb\n', pmsm.FluxPM);
fprintf('  I_rated  = %.1f A\n', pmsm.I_rated);
fprintf('  N_base   = %.0f rpm\n', pmsm.N_base);
fprintf('  N_max    = %.0f rpm\n', pmsm.N_max);
fprintf('  T_rated  = %.2f Nm\n', pmsm.T_rated);

fprintf('\n=== LUT ===\n');
fprintf('  current grid : %d x %d\n', numel(PMSMLUT.idVec), numel(PMSMLUT.iqVec));
fprintf('  Ld range     : %.1f .. %.1f uH\n', min(PMSMLUT.LdTable(:))*1e6, max(PMSMLUT.LdTable(:))*1e6);
fprintf('  Lq range     : %.1f .. %.1f uH\n', min(PMSMLUT.LqTable(:))*1e6, max(PMSMLUT.LqTable(:))*1e6);
fprintf('  torque grid  : %d pts, %.1f .. %.1f Nm\n', ...
    numel(PMSMLUT.trefVec), min(PMSMLUT.trefVec), max(PMSMLUT.trefVec));
fprintf('  speed grid   : %d pts, %.0f .. %.0f rpm\n', ...
    numel(PMSMLUT.wrpmVec), min(PMSMLUT.wrpmVec), max(PMSMLUT.wrpmVec));

maxMotorCurrent = pmsm.I_rated;

%% Per-unit system
% NOTE: on this toolchain mcb_SetPUSystem / mcb_getBaseSpeed fail with
%   "undefined function 'sqrt' for input arguments of type 'int64'"
% inside mcb.internal.PMSMSpeedCurrentsFcn. We therefore derive the base
% quantities analytically:
%   V_base = Vdc/sqrt(3)          (SVPWM linear range)
%   I_base = inverter.ISenseMax   (current sensing range)
%   N_base = V_base / (p * FluxPM) in mechanical rad/s -> rpm
%            (base speed with only the permanent-magnet flux, no saliency)
V_base = inverter.V_dc / sqrt(3);
I_base = inverter.ISenseMax;
omega_base_elec = V_base / pmsm.FluxPM;          % elec rad/s
N_base_rpm = omega_base_elec / pmsm.p * 60/(2*pi);

pmsm.N_base = N_base_rpm;

PU_System = struct();
PU_System.V_base = V_base;
PU_System.I_base = I_base;
PU_System.N_base = N_base_rpm;
PU_System.P_base = (3/2) * V_base * I_base;
% T_base: use the same definition the MathWorks template uses
% (3/2)*p*FluxPM*I_base. Using the measured rated torque here instead
% produces a wildly wrong speed-loop gain.
PU_System.T_base = (3/2) * pmsm.p * pmsm.FluxPM * I_base;

fprintf('\n=== Per-unit system (analytical) ===\n');
fprintf('  V_base = %.2f V, I_base = %.3f A\n', V_base, I_base);
fprintf('  N_base = %.0f rpm\n', N_base_rpm);
fprintf('  T_base = %.2f Nm\n', pmsm.T_rated);

%% Controller design
IIR_filter_speed.type = 'Low-pass';
IIR_filter_speed.min_speed = 200;
IIR_filter_speed.f_cutoff = IIR_filter_speed.min_speed*pmsm.p/(120/2);
IIR_filter_speed.coeff_Ts = 2*pi*Ts*IIR_filter_speed.f_cutoff/(2*pi*Ts*IIR_filter_speed.f_cutoff + 1);
IIR_filter_speed.coeff_Ts_speed = 2*pi*Ts_speed*IIR_filter_speed.f_cutoff/(2*pi*Ts_speed*IIR_filter_speed.f_cutoff + 1);
IIR_filter_speed.time_const = 1/(2*pi*IIR_filter_speed.f_cutoff);
IIR_filter_speed.delay_ss = 4*IIR_filter_speed.time_const;

Delays.Current_Sensor = Ts;
Delays.Speed_Sensor = Ts;
Delays.Speed_Filter = IIR_filter_speed.delay_ss;
Delays.OM_damping_factor = 1/sqrt(2);
Delays.SO_factor_speed = 1.2;

PI_params = mcb_SetControllerParameters(pmsm, inverter, PU_System, T_pwm, Ts, Ts_speed, Delays);
PI_params.delay_Currents = 1;
PI_params.delay_Position = 1;
% Speed-loop gains come from mcb_SetControllerParameters above. The stock
% template hard-codes Kp_speed=2 / Ki_speed=15, which is tuned for a 5 A
% bench motor; on the 433 A e11 it produces a large steady-state speed error.
% Keep the computed values unless a specific scenario needs otherwise.

fprintf('\n=== Controller ===\n');
fprintf('  Kp_i = %.4f, Ki_i = %.4f\n', PI_params.Kp_i, PI_params.Ki_i);
fprintf('  Kp_s = %.4f, Ki_s = %.4f\n', PI_params.Kp_speed, PI_params.Ki_speed);

%% Scenario — comes from mcb_e11_params.m (edit that file to change it)
run(fullfile(fileparts(mfilename('fullpath')), 'mcb_e11_params.m'));

sim_speed_ref   = SCEN.speed_ref_rpm;
sim_load_torque = SCEN.load_torque_nm;
sim_stop_time   = SCEN.stop_time_s;

fprintf('\n=== Scenario ===\n');
fprintf('  speed ref = %d rpm, load = %d Nm, stop = %.2f s\n', ...
    sim_speed_ref, sim_load_torque, sim_stop_time);

fprintf('\n=== Setup complete ===\n');
