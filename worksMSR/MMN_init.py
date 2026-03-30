import os, random, csv
from psychopy import visual, monitors, sound
import numpy as np
import soundfile as sf

from pypixxlib.datapixx import DATAPixx3

# =================================================================
# TO BE CHANGED BY EXPERIMENTER (ONCE PER PARTICIPANT)
# =================================================================
SUB = "JOH3" # Participant abbreviation
# =================================================================

MRS = 1     # 0=no, 1=yes

# -------------------------- PATHS -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # script location
STIM_DIR = os.path.join(BASE_DIR, "MMN-stimuli")
SUB_DIR  = os.path.join(BASE_DIR, "MMN-data", SUB)
#os.makedirs(SUB_DIR, exist_ok=True) # make the folder if doesn't exist already

# Define the full paths to the stimulus files.
STD_FILE    = os.path.join(STIM_DIR, "STD_633Hz_50ms.wav")
DDEV_FILE   = os.path.join(STIM_DIR, "DDEV_1000Hz_100ms.wav")
MOVIE_RUN1  = os.path.join(STIM_DIR, "Pink_Panther_cartoon_1.mp4")
MOVIE_RUN2  = os.path.join(STIM_DIR, "Pink_Panther_cartoon_2.mp4")

# Dictionary to map run number to movie file. This will be used in the preload function.
MOVIE_FOR_RUN = {1: MOVIE_RUN1, 2: MOVIE_RUN2}

# Reserve a thin strip at the left edge so the trigger pixel is not covered by movie content.
PIXEL_MODE_STRIP_PX = 2

# -------------------------- TRIGGERS --------------------
TRIG_STD        = 200
TRIG_DDEV       = 400

TRIG_RUN_START  = 800
TRIG_RUN_END    = 900

# ------------------- TRIAL STRUCTURE ----------------------------
# move stuff here?

# -------------------------- GENERATE TRIAL SEQUENCE --------------------------
def create_participant_sequences(sub_dir, sub_id):
    """
    Generates sequences for both runs and saves them to a single master CSV.
    This function is run once per participant.

    Pseydorandomization logic:
        - Each run has 640 trials: 576 STDs and 64 DDEVs
        - The first 20 trials are always STDs
        - Every DDEV is preceded by at least 3 STDs.
    """
    master_sequence_file = os.path.join(sub_dir, f"{sub_id}_MMN_master_trial_sequence.csv")
    
    # Check if file already exists to avoid overwriting
    if os.path.exists(master_sequence_file):
        print(f"INFO: Master sequence file for {sub_id} already exists. No action taken.")
        return

    print(f"GENERATING: New master sequence file for participant {sub_id}...")
    
    # --- Experiment Constants ---
    TOTAL_TRIALS_PER_RUN = 640
    DDEVS_PER_RUN = 64
    STDS_PER_RUN = TOTAL_TRIALS_PER_RUN - DDEVS_PER_RUN # Should be 576
    INITIAL_STDS = 20
    MIN_STDS_BEFORE_DDEV = 3
    N_RUNS = 2

    all_trials = [] # This list will hold dictionaries for all runs

    for run_num in range(1, N_RUNS + 1):
        
        # --- Step 1: Handle the fixed start of the sequence ---
        # The first 20 trials are always standards.
        initial_sequence = ["STD"] * INITIAL_STDS
        
        # --- Step 2: Calculate standards for the rest of the sequence ---
        # All 64 deviants will be placed in the remaining part of the trial list.
        # Each of these deviants requires a "buffer" of 3 standards immediately before it.
        stds_for_buffer = DDEVS_PER_RUN * MIN_STDS_BEFORE_DDEV # 64 * 3 = 192
        
        # Calculate the remaining standards that are "free" to be placed anywhere.
        stds_available_after_start = STDS_PER_RUN - INITIAL_STDS # 576 - 20 = 556
        free_stds_to_distribute = stds_available_after_start - stds_for_buffer # 556 - 192 = 364

        # --- Step 3: Distribute the "free" standards into slots ---
        # We have 65 possible slots to place these free standards:
        # one before the first deviant block, 63 between the blocks, and one after the last block.
        num_slots = DDEVS_PER_RUN + 1
        stds_in_slots = [0] * num_slots
        
        for _ in range(free_stds_to_distribute):
            # Add one standard to a randomly chosen slot
            random_slot = random.randint(0, num_slots - 1)
            stds_in_slots[random_slot] += 1
            
        # --- Step 4: Construct the randomized part of the sequence ---
        # Build the sequence by combining the free standards and the mandatory 'SSS D' blocks.
        randomized_part = []
        mandatory_block = ["STD"] * MIN_STDS_BEFORE_DDEV + ["DDEV"]
        
        for i in range(DDEVS_PER_RUN):
            # Add the free standards for the slot before this deviant
            randomized_part.extend(["STD"] * stds_in_slots[i])
            # Add the mandatory block itself
            randomized_part.extend(mandatory_block)
            
        # Add the final slot of free standards at the very end
        randomized_part.extend(["STD"] * stds_in_slots[-1])
        
        # --- Step 5: Combine, verify, and format the final sequence ---
        final_sequence = initial_sequence + randomized_part

        # --- Sanity Checks (Crucial to ensure logic is correct) ---
        assert len(final_sequence) == TOTAL_TRIALS_PER_RUN
        assert final_sequence.count("DDEV") == DDEVS_PER_RUN
        assert final_sequence.count("STD") == STDS_PER_RUN
        # Check that every DDEV is preceded by at least 3 STDs
        for i, stim in enumerate(final_sequence):
            if stim == "DDEV":
                # Ensure there's enough space before it and the preceding 3 are STDs
                assert i >= MIN_STDS_BEFORE_DDEV
                assert final_sequence[i-3:i] == ["STD", "STD", "STD"]

        # Convert the generated list into the dictionary format for the master CSV file
        for run_trial_idx, stim_type in enumerate(final_sequence, start=1):
            all_trials.append({
                "run": run_num,
                "trial_index_run": run_trial_idx,
                "stim_type": stim_type
            })

    # Save the complete list of trials for all runs to the master CSV
    with open(master_sequence_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["run", "trial_index_run", "stim_type"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_trials)
        
    print(f"SUCCESS: Master sequence file created at '{master_sequence_file}'")

# -------------------------- INITIALIZE VPIXX DEVICE --------------------------
device = DATAPixx3()

# PIXEL MODE
# enable once
device.dout.enablePixelModeGB()
device.updateRegisterCache() 

# BUTTONBOX
# Initialize buttons
if MRS == 0:
    # Working codes in Lab maestro Simulator
    buttonCodes = {65527:'blue', 65533:'yellow', 65534:'red', 65531:'green', 65519:'white', 65535:'button release'}
    exitButton  = 'white'

if MRS == 1:
    # Button codes in MSR
    buttonCodes = { 65528: 'blue', 65522: 'yellow', 65521: 'red', 65524: 'green', 65520: 'button release' }

myLog = device.din.setDinLog(12e6, 1000) # uses the first 8 DIN slots for buttonbox
device.din.startDinLog()
device.updateRegisterCache()

# MONITOR
def stim_monitor():
    if MRS == 1:
        # "OPM": {"width_cm": 78, "dist_cm": 122, "res_pix": [1920, 1080], "name": "OPM_Monitor", "refresh_rate": 120, "screen_idx": 2}

        # Monitor/Experiment settings 
        viewing_distance_cm 	= 122
        monitor_width_cm    	= 78
        monitor_size_pix    	= [1920, 1080] 
        monitor_name        	= "OPM_Monitor"
        refresh_rate        	= 120
        screen_number           = 2 # 01.22.2026

        # Set Monitor
        monitor = monitors.Monitor(monitor_name) 
        monitor.setWidth(monitor_width_cm)  
        monitor.setDistance(viewing_distance_cm)  
        monitor.setSizePix(monitor_size_pix)
        monitor.save()

        # Set monitor and return information
        return {
            "monitor_size_pix":     monitor_size_pix,
            "monitor_name":         monitor_name,
            "refresh_rate":         refresh_rate,
            "viewing_distance_cm":  viewing_distance_cm,
            "monitor_width_cm":     monitor_width_cm,
            "screen_number":        screen_number
        }

    if MRS == 0:
        # "Laptop": {"width_cm": 34.5, "dist_cm": 40, "res_pix": [1920, 1080], "name": "Laptop", "refresh_rate": 60, "screen_idx": 0},
        viewing_distance_cm 	= 40
        monitor_width_cm    	= 34.5
        monitor_size_pix    	= [1920, 1080] 
        monitor_name        	= "Laptop"
        refresh_rate        	= 60
        screen_number           = 0

        # Set Monitor
        monitor = monitors.Monitor(monitor_name) 
        monitor.setWidth(monitor_width_cm)  
        monitor.setDistance(viewing_distance_cm)  
        monitor.setSizePix(monitor_size_pix)
        monitor.save()

        # Set monitor and return information
        return {
            "monitor_size_pix":     monitor_size_pix,
            "monitor_name":         monitor_name,
            "refresh_rate":         refresh_rate,
            "viewing_distance_cm":  viewing_distance_cm,
            "monitor_width_cm":     monitor_width_cm,
            "screen_number":        screen_number
        }



# -------------------------- AUDIO SETTINGS --------------------------
FS = 48000 # audio sample rate. audio_sampling_frequency # chage to new one, 44000 i think

AUDIO_BASE_ADDR = int(16e6) # adress in vpixx device (where the audio gets stored)

# all 4 below needed for 5th. (5th is the only one to be used in RUN-py)
#HEARING_THRESHOLD = 0.0007 # will be taken from csv

## this is the actual correct one
def load_threshold_csv(thresholdpath):
    # Load Subject-Specific Hearing Threshold
    # thresholdpath = D:\ECYM_S1\ECYM_ASSR\ASSR-data\JOH4\round_2_hearing_threshold_1000.csv
    with open(thresholdpath, "r", encoding="utf-8") as f:
        #reader = csv.DictReader(f)
        reader = csv.DictReader(f, delimiter=';')
        row = next(reader)
    
    print(row.keys())
    print(row)

    return {
        "subject_id": row["subject_id"],
        "threshold_db": float(row["threshold_db"]),
        "threshold_amplitude": float(row["threshold_amplitude"]),
        }

def _load_wav_float32(audiofilespath):
    # Load .wav tone files
    audiofile, samplingfreq = sf.read(audiofilespath, dtype='float32')
    if audiofile.ndim > 1:  # convert to mono if needed
        audiofile   = audiofile.mean(axis=1).astype('float32')
    # create array
    audiofile = np.ascontiguousarray(audiofile, dtype=np.float32)
    peak = float(np.max(np.abs(audiofile))) or 1.0 # get max value

    return audiofile, int(samplingfreq), peak 
    
def preload_tones(vpdevice, paths):
    # preload tones into buffer
    reg = {}
    vpdevice.audio.stopSchedule()

    # check length
    loaded        = {}
    total_samples = 0
    common_fs     = None # assume same samling freq

    for name, p in paths.items():
        x, fs, peak = _load_wav_float32(p)
        x = np.asarray(x, dtype=np.float32).squeeze()
        
        if x.ndim != 1:
            raise ValueError(f"Tone '{name}' is not mono (shape {x.shape})")
            
        if common_fs is None:
            common_fs = fs
        elif fs != common_fs:
            raise ValueError(
                f"All tones must have same fs; '{name}' has {fs}, expected {common_fs}"
            )
            
        n_samples       = len(x)
        loaded[name]    = (x, fs, peak, n_samples)
        total_samples   += n_samples
        
    base_addr = AUDIO_BASE_ADDR  # start address to be written
    buf_bytes = int(vpdevice.audio.getBufferSize())
    
    print(f"[AUDIO] base address (bytes): {base_addr}")
    print(f"[AUDIO] buffer size (bytes): {buf_bytes}")
    print(f"[AUDIO] total samples to write: {total_samples} -> {total_samples * 2} bytes")
    
    bytes_needed = total_samples * 2

    # build one big bank
    all_arrays = [loaded[name][0] for name in paths.keys()]
    audio_bank = np.concatenate(all_arrays).astype(np.float32)

    # writes at 16e6 internally; passing base_addr keeps intent consistent
    vpdevice.audio.writeAudioBuffer(audio_bank, bufferAddress=base_addr)
    vpdevice.updateRegisterCache()

    # offsets + registry
    offset_samples = 0
    for name in paths.keys():
        x, fs, peak, n_samples = loaded[name]
        
        addr_bytes = base_addr + offset_samples * 2
        
        reg[name] = {
            "addr": addr_bytes,
            "offset_samples": offset_samples,
            "n": n_samples,
            "fs": fs,
            "peak": peak,
            "gain": None,
        }
        
        print(
            f"[AUDIO] tone '{name}': addr={addr_bytes}, "
            f"n={n_samples}, offset_samples={offset_samples}"
        )
        
        offset_samples += n_samples
    return reg

#def assign_subject_gains(in_audio_reg, threshold_linear, per_tone_dBSL, master=1.0):
    # include gain in the register
#    for name, info in in_audio_reg.items():
 #       peak            = info.get('peak', 1.0)
   #     this_dBSL       = per_tone_dBSL.get(name)
  #      gain            = master * threshold_linear * (10.0 ** (this_dBSL / 20.0)) / max(peak, 1e-12)
    #    info['gain']    = float(max(0.0, min(1.0, gain)))  # clamp to [0,1]
    #return in_audio_reg
    
def assign_subject_gains(in_audio_reg, threshold_linear, per_tone_dBSL, master=1.0):
    for name, info in in_audio_reg.items():
        peak = info.get('peak', 1.0)
        this_dBSL = per_tone_dBSL.get(name)
        
        if this_dBSL is None:
            raise ValueError(f"No dBSL defined for tone '{name}'")
        
        if peak is None:
            raise ValueError("peak is None – audio not loaded or computed correctly")
            
        gain = master * threshold_linear * (10.0 ** (this_dBSL / 20.0)) / max(peak, 1e-12)
        info['gain'] = float(max(0.0, min(1.0, gain)))

    return in_audio_reg

# -------------------------- PRELOAD STIMULI AND TEXT ---------------
def preload_stim(win, run_number, stimulipath, subjectpath, vpdevice, dB_SL=60):
    """
    if MRS == 0:
        # ======= AUDITORY
        std_sound = sound.Sound(STD_FILE)
        ddev_sound = sound.Sound(DDEV_FILE)

        threshold_volume = 0.0007  
        sound.backend = 'ptb'
        sound.init(rate=44100, stereo=True, buffer=256)
        db_above_threshold = 60
        attenuation_factor = 10 ** (db_above_threshold / 20)
        SOUND_VOLUME = threshold_volume * attenuation_factor
        if SOUND_VOLUME > 1.0:
            print(f"WARNING: volume {SOUND_VOLUME:.2f} too high, capping at 1.0")
            SOUND_VOLUME = 1.0
        else:
            print(f"Sound volume set to {SOUND_VOLUME:.4f}")

        # ======= VISUAL
        # Select the correct movie file based on the run number
        selected_movie_file = MOVIE_FOR_RUN[run_number]

        # Keep a small left margin free for Pixel Mode trigger readout.
        movie_width = max(1, int(win.size[0]) - PIXEL_MODE_STRIP_PX)
        movie_height = int(win.size[1])
        movie_pos_x = PIXEL_MODE_STRIP_PX / 2
        
        movie = visual.MovieStim(
            win,
            selected_movie_file,
            loop=True,
            noAudio=True,
            size=(movie_width, movie_height),
            pos=(movie_pos_x, 0),
            units='pix'
        )
        
        return {"std_sound": std_sound, "ddev_sound": ddev_sound, "movie": movie}
        """
        
    if MRS == 1:
        # ======= AUDITORY
        # create tone register/s
        audio_reg = preload_tones(vpdevice, {
           'STD':   os.path.join(stimulipath, 'sounds', 'STD_633Hz_50ms.wav'),
           'DEV':   os.path.join(stimulipath, 'sounds', 'DDEV_1000Hz_100ms.wav')
        })
        
        # load threshold
        #print(subjectpath)
        thresholdpath = os.path.join(subjectpath, "round_2_hearing_threshold_1000.csv")
        #print(thresholdpath)
        thr_info  = load_threshold_csv(thresholdpath)
        thr_lin   = thr_info["threshold_amplitude"] # eg 0.00024
        
        # assign gains (using audio_reg and thr_lin)
        #audio_reg = assign_subject_gains(audio_reg, threshold_linear=thr_lin, per_tone_dBSL={'Aud_X': dB_SL, 'Aud_Y': dB_SL, 'Aud_FB': dB_SL-10}) # ADD FOR mmn
        audio_reg = assign_subject_gains( audio_reg, threshold_linear=thr_lin, per_tone_dBSL={'STD': dB_SL, 'DEV': dB_SL})
        print(audio_reg)     
        
        
        # ======= VISUAL
        # Select the correct movie file based on the run number
        selected_movie_file = MOVIE_FOR_RUN[run_number]
        
        # Keep a small left margin free for Pixel Mode trigger readout.
        movie_width = max(1, int(win.size[0]) - PIXEL_MODE_STRIP_PX)
        movie_height = int(win.size[1])
        movie_pos_x = PIXEL_MODE_STRIP_PX / 2
        
        movie = visual.MovieStim(
            win,
            selected_movie_file,
            loop=True,
            noAudio=True,
            size=(movie_width, movie_height),
            pos=(movie_pos_x, 0),
            units='pix'
        )
        
        return {"audio": audio_reg, "movie": movie}



def preload_txt(win):
    txt_intro = visual.TextStim(win, text="Sie werden einen Film sehen.\n\n Bitte konzentrieren Sie sich auf den Film und ignorieren Sie die Töne.\n\n Drücken Sie einen beliebigen Knopf, um zu starten.", height=1, pos=(0, 0), units='deg', color='black')
    txt_finished = visual.TextStim(win, text="Dieser Durchgang ist beendet.\n\n Bitte warte auf die Anweisungen.", height=1, pos=(0, 0), units='deg', color='black')
    return {"txt_intro": txt_intro, "txt_finished": txt_finished}


# =================================================================
# This block makes the script executable for one-time setup
# =================================================================
if __name__ == "__main__":
    print("=====================================================")
    print(f"RUNNING ONE-TIME SETUP FOR PARTICIPANT: {SUB}")
    print("=====================================================")
    # Ensure the subject's directory exists before creating the sequence file
    os.makedirs(SUB_DIR, exist_ok=True)
    # Create the master sequence file
    create_participant_sequences(SUB_DIR, SUB)
    print("\nSetup complete. You can now run the MMN paradigm script.")