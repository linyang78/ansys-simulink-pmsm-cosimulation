function pmsm = mcb_SetPMSMMotorParameters(pmsm_type)
% File          :   PMSM Parameter File
% Description   :   Parameters for PMSMs supported by MCB

% Copyright 2020-2022 The MathWorks, Inc.

%%
% Get basic parameters
switch pmsm_type
    case 'BLY171D'
        pmsm.model    = 'Anaheim-BLY171D-24V-4000';%    // Manufacturer Model Number
        pmsm.sn       = '001';              %           // Manufacturer Model Number
        pmsm.p        = 4;                  %           // Pole Pairs for the motor
        pmsm.Rs       = 0.75;               %Ohm        // Stator Resistor
        pmsm.Ld       = 1.05e-3;            %H          // D-axis inductance value
        pmsm.Lq       = 1.05e-3;            %H          // Q-axis inductance value
        pmsm.J        = 2.4018552467e-06;   %Kg-m2      // Inertia in SI units
        pmsm.B        = 11.603710493e-06;   %Kg-m2/s    // Friction Co-efficient
        pmsm.Ke       = 3.8;                %Bemf Const	// Vpk_LL/krpm
        pmsm.Kt       = 0.03396;            %Nm/A       // Torque constant
        pmsm.I_rated  = 1.8;                %A      	// Rated current (phase-peak)
        pmsm.N_max    = 10000;              %rpm        // Max speed
        pmsm.PositionOffset = 0.2016/4;	    %PU position// Position Offset 
        pmsm.QEPSlits = 1250;               %           // QEP Encoder Slits
        pmsm.FluxPM   = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
        pmsm.T_rated  = mcbPMSMRatedTorque(pmsm);   %Get T_rated from I_rated
        
    case 'BLY172S'
        pmsm.model    = 'Anaheim-BLY172S-24V-4000';%    // Manufacturer Model Number
        pmsm.sn       = '002';              %           // Manufacturer Model Number
        pmsm.p        = 4;                  %           // Pole Pairs for the motor
        pmsm.Rs       = 0.4;                %Ohm        // Stator Resistor
        pmsm.Ld       = 0.6e-3;             %H          // D-axis inductance value
        pmsm.Lq       = 0.6e-3;             %H          // Q-axis inductance value
        pmsm.J        = 4.8018552467e-06;   %Kg-m2      // Inertia in SI units
        pmsm.B        = 9.6037104933e-06;   %Kg-m2/s    // Friction Co-efficient
        pmsm.Ke       = 4;                  %Bemf Const	// Vpk_LL/krpm
        pmsm.Kt       = 0.04103;            %Nm/A       // Torque constant
        pmsm.I_rated  = 3.5;                %A      	// Rated current (phase-peak)
        pmsm.N_max    = 10000;              %rpm        // Max speed
        pmsm.PositionOffset = 0.1712;	    %PU position// Position Offset
        pmsm.QEPSlits = 1250;               %           // QEP Encoder Slits
        pmsm.FluxPM   = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
        pmsm.T_rated  = mcbPMSMRatedTorque(pmsm);   %Get T_rated from I_rated
        
    case 'Teknic2310P'
        pmsm.model    = 'Teknic-2310P';     %           // Manufacturer Model Number
        pmsm.sn       = '003';              %           // Manufacturer Model Number
        pmsm.p        = 4;                  %           // Pole Pairs for the motor
        pmsm.Rs       = 0.36;               %Ohm        // Stator Resistor
        pmsm.Ld       = 0.2e-3;             %H          // D-axis inductance value
        pmsm.Lq       = 0.2e-3;             %H          // Q-axis inductance value
        pmsm.J        = 7.061551833333e-6;  %Kg-m2      // Inertia in SI units
        pmsm.B        = 2.636875217824e-6;  %Kg-m2/s    // Friction Co-efficient
        pmsm.Ke       = 4.64;               %Bemf Const	// Vpk_LL/krpm
        pmsm.Kt       = 0.0384;             %Nm/A       // Torque constant
        pmsm.I_rated  = 7.1;                %A      	// Rated current (phase-peak)
        pmsm.N_max    = 6000;               %rpm        // Max speed
        pmsm.PositionOffset = 0.1712;	    %PU position// Position Offset
        pmsm.QEPSlits = 1000;               %           // QEP Encoder Slits
        pmsm.FluxPM   = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
		% pmsm.FluxPM = (pmsm.Kt)/((3/2)*pmsm.p); %PM flux computed from Kt
        pmsm.T_rated  = mcbPMSMRatedTorque(pmsm);   %Get T_rated from I_rated
        
    case 'Maxon_EC_Speedgoat'
        pmsm.model    = 'Maxon-645106';     %           // Manufacturer Model Number
        pmsm.sn       = '2295588';          %           // Manufacturer Model Number     
        pmsm.p        = 7;                  %           // Pole Pairs for the motor
        pmsm.Rs       = 0.293;              %Ohm        // Stator Resistor
        pmsm.Ld       = 87.678e-6;          %H          // D-axis inductance value
        pmsm.Lq       = 77.724e-6;          %H          // Q-axis inductance value
        pmsm.Ke       = 5.7835;             %Bemf Const	// Vpk_LL/krpm
        pmsm.J        = 83.5e-6;            %Kg-m2      // Inertia in SI units
        pmsm.B        = 70.095e-6;          %Kg-m2/s    // Friction Co-efficient
        pmsm.I_rated  = 7.26;               %A      	// Rated current (phase-peak)
        pmsm.QEPSlits = 4096;               %           // QEP Encoder Slits
        pmsm.N_base   = 3700;               %rpm        // Base speed     
        pmsm.N_max    = 4300;               %rpm        // Max speed
        pmsm.FluxPM   = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
        pmsm.T_rated  = mcbPMSMRatedTorque(pmsm);   %Get T_rated from I_rated

    case 'Adlee'                            %           // Interior PMSM
        pmsm.model    = 'ADLEE-BM-180E';    %           // Manufacturer Model Number
        pmsm.sn       = '004';              %           // Manufacturer Model Number     
        pmsm.p        = 4;                  %           // Pole Pairs for the motor
        pmsm.Rs       = 0.1458;             %Ohm        // Stator Resistor
        pmsm.Ld       = 1.3016e-4;          %H          // D-axis inductance value
        pmsm.Lq       = 1.4098e-4;          %H          // Q-axis inductance value
        pmsm.Ke       = 8.8590;             %Bemf Const	// Vpk_LL/krpm
        pmsm.J        = 1.7052e-4;          %Kg-m2      // Inertia in SI units
        pmsm.B        = 1.8667e-4;          %Kg-m2/s    // Friction Co-efficient
        pmsm.I_rated  = 9.3;                %A      	// Rated current (phase-peak)
        pmsm.QEPSlits = 128;                %           // QEP Encoder Slits
        pmsm.N_base   = 2000;               %rpm        // Base speed     
        pmsm.N_max    = 2500;               %rpm        // Max speed
        pmsm.PositionOffset = 0.1934;	    %PU position// Position Offset
        pmsm.FluxPM   = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
        pmsm.T_rated  = mcbPMSMRatedTorque(pmsm);   %Get T_rated from I_rated


    case 'e11'
        pmsm.model    = 'BMW-i3-e11-IPM';   %           // Model name
        pmsm.sn       = 'e11';              %           // Serial number
        pmsm.p        = 4.0;                %           // Pole pairs
        pmsm.Rs       = 0.013377;        %Ohm        // Stator resistance (ECE measured)
        pmsm.Ld       = 1.982000e-04;        %H          // D-axis inductance (ECE, rated point)
        pmsm.Lq       = 3.786000e-04;        %H          // Q-axis inductance (ECE, rated point)
        pmsm.J        = 0.030023;        %Kg-m2      // Total inertia (Motor-CAD measured)
        pmsm.B        = 1.0e-06;             %Kg-m2/s    // Friction coeff (placeholder)
        pmsm.Ke       = 55.0546;             %Bemf Const // Vpk_LL/krpm
        pmsm.Kt       = 0.45530;           %Nm/A       // Torque constant
        pmsm.I_rated  = 433.0;              %A          // Peak current (ECE grid limit)
        pmsm.N_max    = 10000.0;            %rpm        // Max speed
        pmsm.PositionOffset = 0.0;          %PU position// No hardware offset in simulation
        pmsm.QEPSlits = 1000.0;             %           // QEP Encoder Slits
        pmsm.FluxPM   = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
        pmsm.T_rated  = mcbPMSMRatedTorque(pmsm);   %Get T_rated from I_rated

    otherwise
        disp('Creating new parameter structure.');
        pmsm.model    = 'new';              %           // Manufacturer Model Number
        pmsm.sn       = '005';              %           // Manufacturer Model Number
        pmsm.p        = 1;                  %           // Pole Pairs for the motor
        pmsm.Rs       = 1;                  %Ohm        // Stator Resistor
        pmsm.Ld       = 1e-3;               %H          // D-axis inductance value
        pmsm.Lq       = 1e-3;               %H          // Q-axis inductance value
        pmsm.J        = 1e-6;               %Kg-m2      // Inertia in SI units
        pmsm.B        = 1e-6;               %Kg-m2/s    // Friction Co-efficient
        pmsm.Ke       = 1;                  %Bemf Const	// Vpk_LL/krpm
        pmsm.Kt       = 1;                  %Nm/A       // Torque constant
        pmsm.I_rated  = 1;                  %A      	// Rated current (phase-peak)
        pmsm.N_max    = 1;                  %rpm        // Max speed
        pmsm.PositionOffset = 1;		    %PU position// Position Offset
        pmsm.QEPSlits = 1;                  %           // QEP Encoder Slits
        pmsm.FluxPM   = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60); %PM flux computed from Ke
        pmsm.T_rated  = mcbPMSMRatedTorque(pmsm);   %Get T_rated from I_rated
end
if evalin('base', 'exist(''motorParam'', ''var'')')
    if evalin('base', 'numel(fieldnames(motorParam))') >= 9
        motorParam = evalin('base', 'motorParam');    
        if evalin('base', 'isfield(motorParam,''FluxPM'')')     % Check if the parameters are for PMSM
            pmsm.p      = motorParam.p;         %           // Pole Pairs for the motor
            pmsm.Rs     = motorParam.Rs;	    %Ohm        // Shunt Resistor
            pmsm.Ld     = motorParam.Ld;	    %H          // D-axis inductance value
            pmsm.Lq     = motorParam.Lq;	    %H          // Q-axis inductance value
            pmsm.J      = motorParam.J;         %Kg-m2      // Inertia in SI units
            pmsm.B      = motorParam.B;         %Kg-m2/s    // Friction Co-efficient
            pmsm.Ke     = motorParam.Ke;	    %Bemf Const	// Vpk_LL/krpm
            pmsm.FluxPM = (pmsm.Ke)/(sqrt(3)*2*pi*1000*pmsm.p/60);  %PM flux computed from Ke
		    pmsm.Kt     = (3/2) * pmsm.p * pmsm.FluxPM;			%Nm/A // Torque constant
            pmsm.I_rated= motorParam.nomCurrent;              	%A    // Rated current (phase-peak)
		    pmsm.T_rated= mcbPMSMRatedTorque(pmsm);             %     // Get T_rated from I_rated
            pmsm.PositionOffset = motorParam.PositionOffset;    %     // PU angle for Hall Offset
		    pmsm.QEPSlits = motorParam.QEPSlits;				%     // Number of slits in quadrature encoder
			disp('The pmsm structure is updated based on motorParam structure ');
            disp(' (from the Parameter Estimation workflow) in the base workspace.');
        end
    end
end
end
