from __future__ import print_function
import os
import re
import sys
import time
import glob
import fileinput


class NoUVFilesException(Exception):
    pass


def replace(file, pattern, subst):
    """Replace `pattern` on `subst` in `file`.
    """
# Read contents from file as a single string
    file_handle = open(file, 'r')
    file_string = file_handle.read()
    file_handle.close()

# Use RE package to allow for replacement (also allowing for (multiline) REGEX)
    file_string = (re.sub(pattern, subst, file_string))

# Write contents to file.
# Using mode 'w' truncates the file.
    file_handle = open(file, 'w')
    file_handle.write(file_string)
    file_handle.close()


def grab_SNR(fname):
    """Return list of values after `SNR=` in the end of each string.
    """

    results = list()

    with open(fname) as file:
        for line in file:
            if "SNR=" in line:
                result = line.split()[-1]
                results.append(result)

    return results


def replace(file, pattern, subst):
    """Replace `pattern` on `subst` in `file`.
    """
# Read contents from file as a single string
    file_handle = open(file, 'r')
    file_string = file_handle.read()
    file_handle.close()

# Use RE package to allow for replacement (also allowing for (multiline) REGEX)
    file_string = (re.sub(pattern, subst, file_string))

# Write contents to file.
# Using mode 'w' truncates the file.
    file_handle = open(file, 'w')
    file_handle.write(file_string)
    file_handle.close()


def check_fits_file(exp_dir, logs_dir):
    """Checks that FITS-file(s) listed in *.cnt file in `exp_dir` do exists.
    Builds list of FITS-files on the basis of logs and checks that all of
    them listed in *.cnt file. If not all - adds them there. If file(s), specified
    in *.cnt file is absened and no files with specified band are found in
    logs_dir => throws NoUVFilesException).
    """

# Find FITS-files listed in *.cnt-file
   # fits_files_cnt = set()
   # with open(glob.glob(exp_dir + "/*.cnt")[0]) as cntf:
   #     for line in cntf.readlines():
   #         if 'UV_FITS:' in line:
   #             fits_file = line.split()[-1]
   #             fits_files_cnt.add(fits_file)

# Find FITS-files with the desired band from logs
    logs_directory = logs_dir + 'raes03jv'
    logs_files = glob.glob(logs_directory + "/*.log")
    fits_files_logs = set()
    for log_file in logs_files:
        with open(log_file) as lf:
            for line in lf.readlines():
                if "Freq=" + str("166") in line:
                    fits_file = log_file.rstrip(".log")
                    fits_file += ".FITS"
                    fits_files_logs.add(fits_file)

# Comment out previous UV_FITS blocks in *.cnt-file
    replace(glob.glob(exp_dir + "/*.cnt")[0], "UV_FITS:", "#UV_FITS:")

    current_line_is_FITS = False
    for line in fileinput.input(glob.glob(exp_dir + "/*.cnt")[0], inplace=1):
        print line,
        if line.startswith("#UV_FITS:"):
            current_line_is_FITS = True
        if not line.startswith("#UV_FITS:") and current_line_is_FITS:
            current_line_is_FITS = False
            if fits_files_logs:
                for fits_file in fits_files_logs:
                    line = "UV_FITS:            " + fits_file
                    print line, "\n"

            else:
                raise NoUVFilesException("No FITS-files mentioned in logs of " + str(exp_name))


if __name__ == '__main__':


# band name - frequency mapping
# TODO: add regexp for frequencies
    freq_dict = {"l": "166", "c": "4828", "k": "22228"}
    logs_dir = '/home/difxmgr/exper/'
    #exp_name = 'raes03jv'
    exp_name = sys.argv[1]
    #band = 'l'
    band = sys.argv[2]
    #refant = 'EFLSBERG'
    refant = sys.argv[3]

# Creating experiment directory
    os.chdir('/data/ilya/VLBI/pima/')
    os.mkdir(exp_name)
    os.chdir(exp_name)
    exp_dir = os.getcwd()

# Inserting our variables in tcsh environment
    os.environ['SHELL'] = 'tcsh'
    os.environ['exp_name'] = exp_name
    os.environ['band'] = band
    try:
        os.environ['refant'] = refant
    except IndexError:
        os.environ['refant'] = 'EFLSBERG'

# Creating .cnt-file for our experiment
    os.system("tcsh -c 'new_cnt.sh $exp_name $band'")


# Replacing default reference antenna and allowing for bandpass
# calibration.
    replace(glob.glob(exp_dir + "/*.cnt")[0], 'EFLSBERG', refant)
    replace(glob.glob(exp_dir + "/*.cnt")[0], 'BANDPASS_FILE:      NO # ', 'BANDPASS_FILE:      ')

# Inserting FITS-files with the desired band found in logs to *.cnt-file and
# commenting out previous entries
    check_fits_file(exp_dir, logs_dir)

# Finding out number of scans:
    os.chdir("/data/ilya/pima_scr/")
    text = open(exp_name + "_" + band + ".obs")
    number_of_scans = len(re.findall("#SCA", text.read()))

# PROCEEDING WITH PIMA

# Loading fits-files
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band load'")
    print("waiting 10 secs for loading fits-files. Hope it is enough:)")
    time.sleep(10)

    os.system("tcsh -c get_orbitfile.sh '$exp_name'")
# Coarse fringe-fitting
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band coarse'")
    print("waiting 10 secs for coarse fring-fitting. Hope it is enough:)")
    time.sleep(10)

# Bandpass calibration
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band bpass'")
    print("waiting 10 secs for bandpass calibration. Hope it is enough:)")
    time.sleep(10)

# Fine fringe-fitting and parsing for SNR values
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: RR'")
    time.sleep(10)
    RR = grab_SNR(exp_name + "_" + band + "_fine.log")

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: LL'")
    time.sleep(10)
    LL = grab_SNR(exp_name + "_" + band + "_fine.log")

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: RL'")
    time.sleep(10)
    RL = grab_SNR(exp_name + "_" + band + "_fine.log")

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: LR'")
    time.sleep(10)
    LR = grab_SNR(exp_name + "_" + band + "_fine.log")

    print("RR, LL, RL, LR :")
    print(RR)
    print(LL)
    print(RL)
    print(LR)
