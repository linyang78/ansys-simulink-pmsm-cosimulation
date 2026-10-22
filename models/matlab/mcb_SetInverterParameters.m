function inverter = mcb_SetInverterParameters(inverter_type)
% File          :   Inverter Parameter File
% Description   :   Parameters for Inverters supported by MCB

% Copyright 2020-2022 The MathWorks, Inc.

%%
% Get basic parameters
switch inverter_type
    case 'BoostXL-DRV8301'
        inverter.model         = 'BoostXL-DRV8301';		% 		// Manufacturer Model Number
        inverter.sn            = 'INV_XXXX';        	% 		// Manufacturer Serial Number
        inverter.V_dc          = 24;       				%V		// DC Link Voltage of the Inverter
        inverter.I_trip        = 10;       				%Amps   // Max current for trip
        inverter.Rds_on        = 6.5e-3;   				%Ohms   // Rds ON for BoostXL-DRV8301
        inverter.Rshunt        = 0.010;    				%Ohms   // Rshunt for BoostXL-DRV8301
        inverter.CtSensAOffset = 2048;     				%Counts // ADC Offset for phase-A
        inverter.CtSensBOffset = 2048;     				%Counts // ADC Offset for phase-B
        inverter.ADCGain       = 1;        				%       // ADC Gain factor scaled by SPI
        inverter.EnableLogic   = 1;    					% 		// Active high for DRV8301 enable pin (EN_GATE)
        inverter.invertingAmp  = 1;   					% 		// Currents entering motor phases are read as positive values in this hardware
        inverter.ISenseVref    = 3.3;					%V 		// Voltage ref of inverter current sense circuit
        inverter.ISenseVoltPerAmp = 0.1; 				%V/Amps // Current sense voltage output per 1 A current (Rshunt * iSense op-amp gain)
        inverter.ISenseMax    = inverter.ISenseVref/(2*inverter.ISenseVoltPerAmp); %Amps // Maximum Peak-Neutral current that can be measured by inverter current sense
        %     // 'I_max' is replaced by 'IsenseMax'
    case 'BoostXL-DRV8305'
        inverter.model         = 'BoostXL-DRV8305'; 	% 		// Manufacturer Model Number
        inverter.sn            = 'INV_XXXX';         	% 		// Manufacturer Serial Number
        inverter.V_dc          = 24;       				%V      // DC Link Voltage of the Inverter
        inverter.I_trip        = 10;       				%Amps   // Max current for trip
        inverter.Rds_on        = 2e-3;     				%Ohms   // Rds ON for BoostXL-DRV8305
        inverter.Rshunt        = 0.007;    				%Ohms   // Rshunt for BoostXL-DRV8305
        inverter.CtSensAOffset = 2295;        			%Counts // ADC Offset for phase-A
        inverter.CtSensBOffset = 2286;        			%Counts // ADC Offset for phase-B
        inverter.CtSensCOffset = 2295;        			%Counts // ADC Offset for phase-C
        inverter.ADCGain       = 1;                     %       // ADC Gain factor scaled by SPI
        inverter.EnableLogic   = 1;    					% 		// Active high for DRV8305 enable pin (EN_GATE)
        inverter.invertingAmp  = 1;   					% 		// Currents entering motor phases are read as positive values in this hardware
        inverter.ISenseVref    = 3.3;					%V 		// Voltage ref of inverter current sense circuit
        inverter.ISenseVoltPerAmp = 0.07; 				%V/Amps // Current sense voltage output per 1 A current (Rshunt * iSense op-amp gain)
        inverter.ISenseMax     = inverter.ISenseVref/(2*inverter.ISenseVoltPerAmp); %Amps // Maximum Peak-Neutral current that can be measured by inverter current sense

    case 'DRV8312-C2-KIT'
        inverter.model         = 'DRV8312-C2-KIT'; 		% 		// Manufacturer Model Number
        inverter.sn            = 'INV_XXXX';        	% 		// Manufacturer Serial Number
        inverter.V_dc          = 24;       				%V      // DC Link Voltage of the Inverter
        inverter.I_trip        = 9.7;      				%Amps   // Max current for trip
        inverter.Rds_on        = 80e-3;    				%Ohms   // Rds ON for BoostXL-DRV8312
        inverter.Rshunt        = 0.010;    				%Ohms   // Rshunt for BoostXL-DRV8318
        inverter.CtSensAOffset = 2052;        			%Counts // ADC Offset for phase-A
        inverter.CtSensBOffset = 2043;        			%Counts // ADC Offset for phase-B
        inverter.ADCGain       = 1;        				%       // ADC Gain factor scaled by SPI
        inverter.EnableLogic   = 1;    					% 		// Active high for enable pin of inverter
        inverter.invertingAmp  = -1;  					% 		// Currents entering motor phases are read as negative values in this hardware
        inverter.ISenseVref    = 3.3;					%V 		// Voltage ref of inverter current sense circuit
        inverter.ISenseVoltPerAmp = 0.1908;				%V/Amps // Current sense voltage output per 1 A current (Rshunt * iSense op-amp gain)
        inverter.ISenseMax     = inverter.ISenseVref/(2*inverter.ISenseVoltPerAmp); %Amps // Maximum Peak-Neutral current that can be measured by inverter current sense

    case 'BOOSTXL-3PhGaNInv'
        inverter.model         = 'BOOSTXL-3PhGaNInv'; 	% 		// Manufacturer Model Number
        inverter.sn            = 'INV_XXXX';         	% 		// Manufacturer Serial Number
        inverter.V_dc          = 24;       				%V      // DC Link Voltage of the Inverter
        inverter.I_trip        = 12;                   	%Amps   // Max current for trip
        inverter.Rds_on        = 20e-3;    				%Ohms   // Rds ON for BOOSTXL-3PhGaNInv
        inverter.Rshunt        = 0.005;    				%Ohms   // Rshunt for BOOSTXL-3PhGaNInv
        inverter.CtSensAOffset = 2247;        			%Counts // ADC Offset for phase-A
        inverter.CtSensBOffset = 2245;        			%Counts // ADC Offset for phase-B
        inverter.ADCGain       = 1;        				%       // ADC Gain factor scaled by SPI
        inverter.EnableLogic   = 0;    					% 		// Active low for enable pin of GaN inverter
        inverter.invertingAmp  = -1;  					% 		// Currents entering motor phases are read as negative values in this hardware
        inverter.ISenseVref    = 3.3;					%V 		// Voltage ref of inverter current sense circuit
        inverter.ISenseVoltPerAmp = 0.1;				%V/Amps // Current sense voltage output per 1 A current (Rshunt * iSense op-amp gain)
        inverter.ISenseMax     = inverter.ISenseVref/(2*inverter.ISenseVoltPerAmp); %Amps // Maximum Peak-Neutral current that can be measured by inverter current sense

    case 'Speedgoat_PWR-TPI6020'
        inverter.model         = 'Speedgoat_PWR-TPI6020';% 		// Manufacturer Model Number
        inverter.sn            = 'INV_XXXX';         	% 		// Manufacturer Serial Number
        inverter.V_dc          = 24;       				%V      // DC Link Voltage of the Inverter
        inverter.I_trip        = 30;                   	%Amps   // Max current for trip
        inverter.CtSensAOffset = 0.0942;         		%Counts // ADC Offset for phase-A
        inverter.CtSensBOffset = -0.00255;        		%Counts // ADC Offset for phase-B
        inverter.Rds_on        = 1e-3;     				%Ohms   // Rds ON dummy value
        inverter.Rshunt        = 1e-3;     				%Ohms   // Rshunt dummy value
        inverter.ISenseVref    = 5.12;					%V 		// Voltage ref of inverter current sense circuit
        inverter.ISenseVoltPerAmp = 66.6e-3;			%V/Amps // Current sense voltage output per 1 A current (Rshunt * iSense op-amp gain)
        inverter.ISenseMax     = inverter.ISenseVref/(2*inverter.ISenseVoltPerAmp); %Amps // Maximum Peak-Neutral current that can be measured by inverter current sense


    case 'e11-inverter'
        % Generic high-current inverter sized for the e11 traction machine.
        % The e11 peaks at 433 A; BoostXL boards (10-23 A) cannot cover it, and
        % per-unit scaling in the controller design uses ISenseMax as I_base,
        % so an undersized value corrupts every PI gain.
        inverter.model         = 'e11-generic-500A';  %           // Model name
        inverter.sn            = 'INV_e11';           %           // Serial number
        inverter.V_dc          = 400.0;               %V          // DC link voltage
        inverter.I_trip        = 500.0;             %Amps       // Over-current trip level
        inverter.Rds_on        = 2e-3;                %Ohms       // Switch on-resistance (placeholder)
        inverter.Rshunt        = 0.001;               %Ohms       // Current shunt
        inverter.CtSensAOffset = 2295;                %Counts     // ADC offset phase A
        inverter.CtSensBOffset = 2286;                %Counts     // ADC offset phase B
        inverter.CtSensCOffset = 2295;                %Counts     // ADC offset phase C
        inverter.ADCGain       = 1;                   %           // ADC gain
        inverter.EnableLogic   = 1;                   %           // Active-high enable
        inverter.invertingAmp  = 1;                   %           // Positive current convention
        inverter.ISenseVref    = 3.3;               %V          // Current-sense reference
        inverter.ISenseVoltPerAmp = 0.003300;        %V/Amps     // Sense volts per amp
        inverter.ISenseMax     = inverter.ISenseVref/(2*inverter.ISenseVoltPerAmp);

    otherwise
        disp('Creating new inverter parameter structure.');
        inverter.model         = 'new'; 				% 		// Manufacturer Model Number
        inverter.sn            = 'INV_XXXX';    		% 		// Manufacturer Serial Number
        inverter.V_dc          = 1;        				%V      // DC Link Voltage of the Inverter
        inverter.I_max         = 1;        				%Amps   //
        inverter.I_trip        = 1;        				%Amps   // Max current for trip
        inverter.Rds_on        = 1e-3;     				%Ohms   // Rds ON
        inverter.Rshunt        = 1e-3;     				%Ohms   // Rshunt
        inverter.CtSensAOffset = 2048;     				%Counts // ADC Offset for phase-A
        inverter.CtSensBOffset = 2048;     				%Counts // ADC Offset for phase-B
        inverter.ADCGain       = 1;        				%       // ADC Gain factor scaled by SPI
        inverter.EnableLogic   = 1;    					%		// Active high for enable pin of inverter
        inverter.invertingAmp  = 1;   					% 		// Currents entering motor phases are read as positive values in this hardware
        inverter.ISenseVref    = 3.3;					%V 		// Voltage ref of inverter current sense circuit
        inverter.ISenseVoltPerAmp = 1;					%V/Amps // Current sense voltage output per 1 A current (Rshunt * iSense op-amp gain)
        inverter.ISenseMax     = inverter.ISenseVref/(2*inverter.ISenseVoltPerAmp);%Amps // Maximum Peak-Neutral current that can be measured by inverter current sense
end

inverter.R_board         = inverter.Rds_on + inverter.Rshunt/3;  %Ohms

inverter.CtSensOffsetMax = 2500; % Maximum permitted ADC counts for current sense offset
inverter.CtSensOffsetMin = 1500; % Minimum permitted ADC counts for current sense offset

end

