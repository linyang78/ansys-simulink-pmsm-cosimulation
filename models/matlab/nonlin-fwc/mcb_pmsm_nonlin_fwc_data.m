% Model         : Interior-PMSM Field Weakening Control
% File name     : mcb_pmsm_nonlin_fwc_data.m
% About         : This file contains the initialization routune for running
%                   the example model


% Copyright 2022 The MathWorks, Inc.

%% Set PWM Switching frequency
PWM_frequency 	= 20e3;         %Hz         // Converter s/w freq
T_pwm           = 1/PWM_frequency;  %s      // PWM switching time period

%% Set Sample Times
Ts          	= T_pwm;        %sec        // Sample time for control system
Ts_simulink     = T_pwm/2;      %sec        // Simulation time step for model simulation
Ts_motor        = T_pwm/2;      %sec        // Simulation sample time for pmsm
Ts_inverter     = T_pwm/2;      %sec        // Simulation time step for inverter
Ts_speed        = 30*Ts;        %sec        // Sample time for speed controller

%% Set data type for the model (simulation)

dataType = 'single';           


%% System Parameters 

load('IPMSM_template_data.mat');  
pmsm.model='pmsm_template';
% To support a custom motor from JMAG
% 1. Get *.rtt from https://www.jmag-international.com/modellibrary/, get
%    RT-Viewer from https://www.jmag-international.com/products/rt-viewer/,
%    and obtain the Type-2(Free) license to download Ld, Lq Maps.
% 2. Export the Ld, Lq Table Values w.r.to the same grid size of id, iq as
%    *.csv files. For ex: save them as JMAG_Ld.csv, and JMAG_Lq.csv
%    (RT Viewer Menu: Table Value -> Inductance -> Id-Iq-Ld; 
%       Map window Menu: File -> Csv Export; 
%       Csv Export window: provide id, iq grid details, and file name )
% 3. Create template structures for pmsm and inverter using a known configuration such as the following
%    % pmsm=mcb_SetPMSMMotorParameters('Teknic2310P');
%    % inverter= mcb_SetInverterParameters("BoostXL-DRV8305")
%    % pmsm.B=pmsm.B*100; % increasing the viscous damping coefficient
%    %   %since this is a bigger motor than the Teknic2310p.
% 4. Read the motor parameters and update the following fields
%    a. pmsm.p  (pole pairs)
%    b. pmsm.Rs (stator/Coil Resistance)
%    c. pmsm.Ld (d_inductance)
%    d. pmsm.Lq (q_inductance)
%    e. pmsm.J  (inertia)
%    f. pmsm.FluxPM (magflux)
%    g. pmsm.I_rated (rated_current)
%    h. inverter.V_dc (rated_voltage)
% 5. Calculate the rated torque using known function
%    pmsm.T_rated=mcbPMSMRatedTorque(pmsm);
% 6. Create a seed structure with the file paths, to read the files
%    % seed.Ldfilepath='JMAG_Ld.csv';
%    % seed.Lqfilepath='JMAG_Lq.csv';
% 7. Create LUTs using an API
%    % PMSMLUT=mcbGenerateTables(pmsm,inverter,'jmagindfiles2inddq',seed);
%    Since we need the FluxPM in the same LUT format, create an array
%    % PMSMLUT.FluxPMTable=pmsm.FluxPM*ones(size(PMSMLUT.LdTable));
% 8. Use the following blocks in the model to use the non-linear LUTs
%    a. LUT based PMSM Control Reference
%    b. PMSM FeedForward Control
%    c. PMSM Torque Estimator
%    The motor parameter input is selected to accept Ld, Lq and FluxPM LUTs
% 9. Use the FEM Parameterized PMSM as the plant model
% 10. Set modelling option to  "2-D partial derivative data | No thermal port"
% 11. Set "Assume sinusoidal back emf- tabulate with d- and q-axis
%     currents" as parameterization setting. 
% 12. Populate the PMSMLUT's fields in their appropriate placesdepending
% on the parameter input method. 
%    a. PMSMLUT.idVec
%    b. PMSMLUT.iqVec
%    c. PMSMLUT.LdTable
%    d. PMSMLUT.LqTable
%    e. PMSMLUT.FluxPMTable
% or 
%    a. PMSMLUT.trefVec
%    b. PMSMLUT.wrpmVec
%    c. PMSMLUT.idTable
%    d. PMSMLUT.iqTable
% 13. Populate rest of the motor parameters in their corresponding places,
% 14. For the PMSM plant, 
%    a. maintain the default value for stator zero sequence inductance
%    b. update pmsm.B and pmsm.J in the mechanical parameters
%    c. set the initial targets for Rotor speed and Rotor angle to 0. 






%% Derive Characteristics
tmpmat=mcbPMSMSpeeds(pmsm,inverter,"outputAll",1);
pmsm=mcbPMSMUpdateLdLqFluxPM(pmsm,PMSMLUT,round(tmpmat(1,1)),round(tmpmat(2,1)),1); % to update Ld, Lq, FluxPM corresponding to rated operating condition
pmsm.N_base = mcb_getBaseSpeed(pmsm,inverter,'actual');  %rpm // Base speed of motor at given Vdc
pmsm.N_max  = mcbPMSMMaxSpeed(pmsm,inverter);   %rpm // Max speed of motor for characteristics
pmsm.T_rated=mcbPMSMRatedTorque(pmsm,inverter);

maxMotorCurrent = pmsm.I_rated;                 %Ampere // Maximum current allowed in motor during operation
% %uncomment the following command to plot the drive characteristics
% mcb_getCharacteristics(pmsm,inverter);

%% PU System details // Set base values for pu conversion

PU_System = mcb_SetPUSystem(pmsm,inverter);

%% Controller design 

% IIR Filter for speed
IIR_filter_speed.type           = 'Low-pass';
IIR_filter_speed.min_speed      = 200; %rpm
IIR_filter_speed.f_cutoff       = IIR_filter_speed.min_speed*pmsm.p/(120/2); %Hz
IIR_filter_speed.coeff_Ts       = 2*pi*Ts*IIR_filter_speed.f_cutoff/(2*pi*Ts*IIR_filter_speed.f_cutoff + 1);
IIR_filter_speed.coeff_Ts_speed = 2*pi*Ts_speed*IIR_filter_speed.f_cutoff/(2*pi*Ts_speed*IIR_filter_speed.f_cutoff + 1);
IIR_filter_speed.time_const     = 1/(2*pi*IIR_filter_speed.f_cutoff);
IIR_filter_speed.delay_ss       = 4*IIR_filter_speed.time_const;

% Sensor Delays
Delays.Current_Sensor           = Ts;       %Current Sensor Delay
Delays.Speed_Sensor             = Ts;       %Speed Sensor Delay
Delays.Speed_Filter             = IIR_filter_speed.delay_ss;    %Delay for Speed filter

% Controller Delays
Delays.OM_damping_factor        = 1/sqrt(2);            %Damping factor for current control loop 
Delays.SO_factor_speed          = 1.2;                  %Speed controller delay factor 1 < x < 20

% Get PI Gains
PI_params = mcb_SetControllerParameters(pmsm,inverter,PU_System,T_pwm,Ts,Ts_speed,Delays);

%Updating delays for simulation
PI_params.delay_Currents    = 1;
PI_params.delay_Position    = 1;


PI_params.Kp_speed=2; %updating the speed gain values
PI_params.Ki_speed=15;

% %Uncomment for frequency domain analysis
% mcb_getControlAnalysis(pmsm,inverter,PU_System,PI_params,Ts,Ts_speed);

%% Displaying model variables
disp(pmsm);
disp(inverter);
disp(PU_System);
