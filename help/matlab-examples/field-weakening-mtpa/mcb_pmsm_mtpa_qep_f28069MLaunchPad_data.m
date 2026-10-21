% Model         :   PMSM Torque Control with MTPA
% Description   :   Set Parameters for PMSM Torque Control with MTPA
% File name     :   mcb_pmsm_mtpa_qep_f28069MLaunchPad_data.m

% Copyright 2020-2022 The MathWorks, Inc.

%% Simulation Parameters

%% Set PWM Switching frequency
PWM_frequency 	= 10e3;    %Hz          // Converter s/w freq
T_pwm           = 1/PWM_frequency;  %s  // PWM switching time period

%% Set Sample Times
Ts          	= T_pwm;        %sec        // Sample time for control system
Ts_simulink     = T_pwm/2;      %sec        // Simulation time step for model simulation
Ts_motor        = T_pwm/2;      %sec        // Simulation sample time for pmsm
Ts_inverter     = T_pwm/2;      %sec        // Simulation time step for inverter
Ts_trq_ctrl     = 100*Ts;       %sec        // Sample time for reference torque generator

%% Set data type for the model (simulation & code-generation)

dataType = 'single';            % Floating point code-generation
% dataType = fixdt(1,32,17);    % Fixed point code-generation

%% System Parameters // Hardware parameters 

% Set motor parameters
% pmsm = mcb_SetPMSMMotorParameters('Teknic2310P');
% pmsm = mcb_SetPMSMMotorParameters('BLY171D');

% Set inverter parameters
inverter = mcb_SetInverterParameters('BoostXL-DRV8305');

% Set target hardware parameters
target = mcb_SetProcessorDetails('F28069M',PWM_frequency);

%% Calibration section

%Update ADC offsets with calibrated values below
% inverter.CtSensAOffset = 2280;
% inverter.CtSensBOffset = 2290;

target.comport = '<Select a port...>';
% target.comport = 'COM3';       % Uncomment and update the appropriate serial port
target.SCI_baud_rate    = 5.625e6;  % Set baud rate for serial communication
target.ADCCalibEnable   = 1;        % Enable : 1, Disable :0 to Auto-calibrate ADCs

%Update custom motor's parameters below
pmsm.model  = 'IPMSM_1';%                   // Manufacturer Model Number
pmsm.sn     = '001';            %           // Manufacturer Model Number
pmsm.p      = 4;                %           // Pole Pairs for the motor
pmsm.Rs     = 0.36;             %Ohm        // Stator Resistor
pmsm.Ld     = 0.2e-3;           %H          // D-axis inductance value
pmsm.Lq     = 5*pmsm.Ld;        %H          // Q-axis inductance value // Assumed saliency (Lq/Ld = 5)
pmsm.J      = 7.0615e-6;        %Kg-m2      // Inertia in SI units
pmsm.B      = 2.6368e-6;        %Kg-m2/s    // Friction Co-efficient
pmsm.Ke     = 4.64;             %Bemf Const	// Vline_peak/krpm
pmsm.Kt     = 0.0384;           %Nm/A       // Torque constant
pmsm.I_rated= 7.1;              %A      	// Rated current (phase-peak)
pmsm.N_max  = 6000;             %rpm        // Max speed

pmsm.FluxPM     = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
pmsm.T_rated    = (3/2)*pmsm.p*pmsm.FluxPM*pmsm.I_rated;   %Get T_rated from I_rated

% %Update QEP position sensor with calibrated value below
pmsm.PositionOffset = 0.1712;   %PU position// QEP Offset for Teknik2310P
pmsm.QEPSlits       = 1000;     %           // QEP Encoder Slits

maxMotorCurrent = pmsm.I_rated; %Ampere // Maximum current allowed in motor during operation

% Update ADC Gain for DRV8305
if pmsm.I_rated < 5
    inverter.ADCGain = 4;   % ADC Range = +- 4.825A wrt 0-4095 counts
    inverter.SPI_Gain_Setting = 0x502A;
    
elseif pmsm.I_rated < 7
    inverter.ADCGain = 2;   % ADC Range = +- 9.650A wrt 0-4095 counts
    inverter.SPI_Gain_Setting = 0x5015;

else     
    inverter.ADCGain = 1;   % ADC Range = +- 19.300A wrt 0-4095 counts       
    inverter.SPI_Gain_Setting = 0x5000;        
    
end

% Voltage output of inverter current sense circuit
inverter.ISenseVoltPerAmp = inverter.ISenseVoltPerAmp * inverter.ADCGain; 

% Update ISenseMax according to set ADC gain
inverter.ISenseMax = inverter.ISenseMax /inverter.ADCGain;

% Max and min ADC counts for current sense offsets
inverter.CtSensOffsetMax = 2500; % Maximum permitted ADC counts for current sense offset
inverter.CtSensOffsetMin = 1500; % Minimum permitted ADC counts for current sense offset

%% Derive Characteristics
pmsm.N_base = mcb_getBaseSpeed(pmsm,inverter); %rpm // Base speed of motor at given Vdc
% mcb_getCharacteristics(pmsm,inverter);

%% PU System details // Set base values for pu conversion

PU_System = mcb_SetPUSystem(pmsm,inverter);

%% Controller design // Get ballpark values!

PI_params = mcb_SetControllerParameters(pmsm,inverter,PU_System,T_pwm,Ts,Ts_trq_ctrl);

%Updating delays for simulation
PI_params.delay_Currents    = 1;
PI_params.delay_Position    = 1;

% %Uncomment for frequency domain analysis
% mcb_getControlAnalysis(pmsm,inverter,PU_System,PI_params,Ts,Ts_speed);

%% Displaying model variables
disp(pmsm);
disp(inverter);
disp(target);
disp(PU_System);
