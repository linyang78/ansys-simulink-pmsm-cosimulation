%% Run the e11 non-linear FWC simulation from parameters
%
% Usage:
%   1. Edit mcb_e11_params.m to set speed / load / stop time
%   2. Run this script
%
% Produces: results/sim/e11_sim_<speed>rpm_<load>Nm.mat and a summary printout.

clear; clc;

root = fileparts(fileparts(fileparts(mfilename('fullpath'))));   % repo root
addpath(fullfile(root, 'models', 'matlab'));
addpath(fullfile(root, 'models', 'matlab', 'nonlin-fwc'));

%% Load parameters and motor model
run(fullfile(root, 'models', 'matlab', 'mcb_e11_nonlin_setup.m'));

%% Load and configure the model
mdl = 'mcb_pmsm_nonlin_fwc';
load_system(mdl);

% Take over initialisation: the model's own InitFcn loads the template motor
set_param(mdl, 'InitFcn', '');
set_param(mdl, 'PreLoadFcn', '');

% Apply scenario to the model's control constants.
% NOTE: the model also carries two KnobBlock widgets ("Speed Reference (RPM)"
% and "Load Torque (Nm)"). They have no output ports and do not drive the
% control path -- the values actually read by the controller live in the two
% Constant blocks below. Setting the knobs does nothing.
set_param([mdl '/Control System/Speed ref RPM'],      'Value', num2str(SCEN.speed_ref_rpm));
set_param([mdl '/Inverter and Motor/Torque ref Nm'],  'Value', num2str(SCEN.load_torque_nm));

set_param(mdl, 'StopTime', num2str(SCEN.stop_time_s));
set_param(mdl, 'Solver',   SCEN.solver);
set_param(mdl, 'MaxStep',  num2str(SCEN.max_step_s));

fprintf('\n=== Running simulation ===\n');
t0 = tic;
simOut = sim(mdl, 'ReturnWorkspaceOutputs', 'on');
fprintf('  done in %.1f s\n', toc(t0));

%% Collect signals
logs = simOut.logsout;
n = logs.numElements;
sig = struct('name', {}, 't', {}, 'y', {});

for k = 1:n
    nm = logs{k}.Name;
    if isempty(nm)
        nm = sprintf('signal%d', k);
    end
    try
        sig(end+1).name = nm;                        %#ok<SAGROW>
        sig(end).t = logs{k}.Values.Time;
        sig(end).y = squeeze(logs{k}.Values.Data);
    catch
    end
end

%% Save
outdir = fullfile(root, 'results', 'sim');
if ~exist(outdir, 'dir')
    mkdir(outdir);
end
outfile = fullfile(outdir, sprintf('e11_sim_%drpm_%dNm.mat', ...
    round(SCEN.speed_ref_rpm), round(SCEN.load_torque_nm)));
save(outfile, 'sig', 'SCEN', 'PU_System', 'pmsm', 'PMSMLUT', 'inverter');
fprintf('  saved: %s\n', outfile);

%% Summary
fprintf('\n=== Results ===\n');
fprintf('  %-24s %8s %12s %12s %12s\n', 'signal', 'pts', 'min', 'max', 'final');
for k = 1:numel(sig)
    y = sig(k).y;
    fprintf('  %-24s %8d %12.4g %12.4g %12.4g\n', ...
        sig(k).name, numel(y), min(y(:)), max(y(:)), y(end));
end

% Physical values
I_base = PU_System.I_base;
N_base = PU_System.N_base;
fprintf('\n=== Physical units ===\n');
for k = 1:numel(sig)
    nm = sig(k).name;
    y = sig(k).y;
    switch nm
        case 'speed_fb'
            fprintf('  speed feedback : %8.1f rpm\n', y(end)*N_base);
        case 'speed_ref'
            fprintf('  speed reference: %8.1f rpm\n', y(end)*N_base);
        case 'Id_fb'
            fprintf('  Id feedback    : %8.1f A\n', y(end)*I_base);
        case 'Iq_fb'
            fprintf('  Iq feedback    : %8.1f A\n', y(end)*I_base);
        case 'Te_PU'
            fprintf('  torque         : %8.2f Nm\n', y(end)*PU_System.T_base);
    end
end

close_system(mdl, 0);
fprintf('\n=== Done ===\n');
