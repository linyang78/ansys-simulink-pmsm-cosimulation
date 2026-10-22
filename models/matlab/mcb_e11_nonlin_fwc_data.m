%% e11 Non-linear PMSM Field-Weakening Control (with MTPA) - data script
% Adapted from the MathWorks "FWCWithMTPAOfNonLinearPMSMUsingLUTExample".
%
% Differences from the original
% ----------------------------
%   * motor    : BMW i3 (e11) IPM, parameters from Motor-CAD ECE export
%   * Ld/Lq    : from ECE 91x91 saturation map (Ld by central difference,
%                Lq by secant PsiQ/Iq - see e11_build_pmsmlut.m)
%   * J        : 0.030023 kg.m2  (Motor-CAD e11_emagnetic_results.csv)
%   * B        : 7.599e-5 kg.m2/s  (30 W friction loss at 6000 rpm)
%   * V_dc     : 400 V
%   * I_rated  : 433 A (ECE grid limit, peak)

clear; clc;

%% Set PWM switching frequency
PWM_frequency   = 20e3;             % Hz
T_pwm           = 1/PWM_frequency;  % s

%% Set sample times
Ts              = T_pwm;
Ts_simulink     = T_pwm/2;
Ts_motor        = T_pwm/2;
Ts_inverter     = T_pwm/2;
Ts_speed        = 30*Ts;

%% Data type
dataType = 'single';

%% ===== Motor parameters (e11) =====
addpath(fullfile(fileparts(mfilename('fullpath'))));

pmsm = mcb_SetPMSMMotorParameters('e11');
pmsm.B = 7.599e-5;      % kg.m2/s, from 30 W friction loss at 6000 rpm
pmsm.p = 4;

fprintf('=== e11 motor ===\n');
fprintf('  Rs   = %.6f ohm\n', pmsm.Rs);
fprintf('  Ld   = %.1f uH   (nominal)\n', pmsm.Ld*1e6);
fprintf('  Lq   = %.1f uH   (nominal)\n', pmsm.Lq*1e6);
fprintf('  J    = %.6f kg.m2\n', pmsm.J);
fprintf('  B    = %.3e kg.m2/s\n', pmsm.B);
fprintf('  FluxPM = %.6f Wb\n', pmsm.FluxPM);
fprintf('  I_rated = %.0f A\n', pmsm.I_rated);

%% ===== Inverter (400 V bus) =====
inverter = mcb_SetInverterParameters('BoostXL-DRV8305');
inverter.V_dc = 400;
inverter.ISenseMax = 433;
fprintf('  V_dc = %.0f V\n', inverter.V_dc);

%% ===== LUT from ECE saturation map =====
ecePath = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'results', ...
    'e11-ece-91x91', 'ECE_e11_91x91_map.mat');
fprintf('\n=== Building PMSMLUT from ECE ===\n');
PMSMLUT = e11_build_pmsmlut(ecePath, pmsm);
pmsm.PMSMLUT = PMSMLUT;

%% ===== Rated torque =====
pmsm.T_rated = mcbPMSMRatedTorque(pmsm, inverter);
fprintf('\n  T_rated = %.2f N.m\n', pmsm.T_rated);

%% ===== Generate id/iq reference-current LUTs =====
fprintf('\n=== Generating id/iq reference LUTs ===\n');
seed = struct();
PMSMLUT = mcbGenerateTables(pmsm, inverter, 'idiqLUTs', seed);
pmsm.PMSMLUT = PMSMLUT;
fprintf('  torque grid : %d pts, %.1f .. %.1f N.m\n', ...
    numel(PMSMLUT.trefVec), min(PMSMLUT.trefVec), max(PMSMLUT.trefVec));
fprintf('  speed grid  : %d pts, %.0f .. %.0f rpm\n', ...
    numel(PMSMLUT.wrpmVec), min(PMSMLUT.wrpmVec), max(PMSMLUT.wrpmVec));

%% ===== Derive characteristics =====
tmpmat = mcbPMSMSpeeds(pmsm, inverter, "outputAll", 1);
pmsm = mcbPMSMUpdateLdLqFluxPM(pmsm, PMSMLUT, round(tmpmat(1,1)), round(tmpmat(2,1)), 1);
pmsm.N_base = mcb_getBaseSpeed(pmsm, inverter, 'actual');
pmsm.N_max  = mcbPMSMMaxSpeed(pmsm, inverter);
pmsm.T_rated = mcbPMSMRatedTorque(pmsm, inverter);

fprintf('\n=== Drive characteristics ===\n');
fprintf('  N_base = %.0f rpm\n', pmsm.N_base);
fprintf('  N_max  = %.0f rpm\n', pmsm.N_max);
fprintf('  T_rated = %.2f N.m\n', pmsm.T_rated);

maxMotorCurrent = pmsm.I_rated;

%% ===== Per-unit system =====
PU_System = mcb_SetPUSystem(pmsm, inverter);

%% ===== Speed filter =====
IIR_filter_speed.type           = 'Low-pass';
IIR_filter_speed.min_speed      = 200;
IIR_filter_speed.f_cutoff       = IIR_filter_speed.min_speed*pmsm.p/(120/2);
IIR_filter_speed.coeff_Ts       = 2*pi*Ts*IIR_filter_speed.f_cutoff/(2*pi*Ts*IIR_filter_speed.f_cutoff + 1);
IIR_filter_speed.coeff_Ts_speed = 2*pi*Ts_speed*IIR_filter_speed.f_cutoff/(2*pi*Ts_speed*IIR_filter_speed.f_cutoff + 1);
IIR_filter_speed.time_const     = 1/(2*pi*IIR_filter_speed.f_cutoff);
IIR_filter_speed.delay_ss       = 4*IIR_filter_speed.time_const;

%% ===== Delays =====
Delays.Current_Sensor = Ts;
Delays.Speed_Sensor   = Ts;
Delays.Speed_Filter   = IIR_filter_speed.delay_ss;
Delays.OM_damping_factor = 1/sqrt(2);
Delays.SO_factor_speed   = 1.2;

%% ===== PI gains =====
PI_params = mcb_SetControllerParameters(pmsm, inverter, PU_System, T_pwm, Ts, Ts_speed, Delays);
PI_params.delay_Currents = 1;
PI_params.delay_Position = 1;

fprintf('\n=== Controller gains ===\n');
fprintf('  Kp_i   = %.5f, Ki_i   = %.5f\n', PI_params.Kp_i, PI_params.Ki_i);
fprintf('  Kp_id  = %.5f, Ki_id  = %.5f\n', PI_params.Kp_id, PI_params.Ki_id);
fprintf('  Kp_speed = %.2f, Ki_speed = %.2f\n', PI_params.Kp_speed, PI_params.Ki_speed);
fprintf('  Kp_fwc = %.5f, Ki_fwc = %.5f\n', PI_params.Kp_fwc, PI_params.Ki_fwc);

fprintf('\n=== e11 data loaded ===\n');
