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


def find_kth_word_in_line(line, k, words, start=None):
    """
    Return  k-th word in line if line does contain specified words, begin with
    specified string or contain specified regular expressions.

    #TODO: implement negatiation

    Inputs:
    	line [str] - line to search,
	k [int] - position of word in line,
	words - iterable of words (strings),
	start [string] - string that line must start from.
    Outputs:
    	None - if no such lines are found in file,
	[str] - k-th word in line, containing words.
    """

    contains = [word in line for word in words]
    if False in contains:
	result = None
    elif start:
	if not line.startswith(start):
	    result = None
	else:
            result = line.split()[k]
    else:
        result = line.split()[k]

    return result
	

def find_kths_words_in_file(fname, klist, words, start=None):
    """
    Return list of k-th words in each line of file if string
    contains specified words.
    Inputs:
    	fname [str] - file name,
	klist [list] - list of positions of words in line
	words - iterable of words (strings),
	start [string] - string that line must start from.
    Outputs:
    	None - if no such lines are found in file,
	[list] - list of lists of strings.
    """

    results = list()

    with open(fname) as file:
        for line in file:
	    line_results = list()
	    for k in klist:
		result = find_kth_word_in_line(line, k, words, start=start) 
		if result:
		    line_results.append(result)
	    if line_results:
	        results.append(line_results)

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


def check_fits_file(exp_name, band, exp_dir, logs_dir):
    """
    Builds list of FITS-files on the basis of logs and adds them to *.cnt-file.
    If no files with specified band are found in logs_dir => throws
    NoUVFilesException.
    """

# Find FITS-files with the desired band from logs
    logs_directory = logs_dir + exp_name 
    logs_files = glob.glob(logs_directory + "/*.log")
    fits_files_logs = set()
    for log_file in logs_files:
        with open(log_file) as lf:
            for line in lf.readlines():
                if "Freq=" + freq_dict[band] in line:
                    fits_file = log_file.rstrip(".log")
                    fits_file += ".FITS"
                    fits_files_logs.add(fits_file)

# Comment out previous UV_FITS blocks in *.cnt-file
    replace(glob.glob(exp_dir + "/*.cnt")[0], "UV_FITS:", "#UV_FITS:")

    current_line_is_FITS = False
    for line in fileinput.input(glob.glob(exp_dir + "/*.cnt")[0], inplace=1):
        print(line.strip())
        if line.startswith("#UV_FITS:"):
            current_line_is_FITS = True
        if not line.startswith("#UV_FITS:") and current_line_is_FITS:
            current_line_is_FITS = False
            if fits_files_logs:
                for fits_file in fits_files_logs:
                    line = "UV_FITS:            " + fits_file
                    print(line.strip())

            else:
                raise NoUVFilesException("No FITS-files mentioned in logs of " + str(exp_name))


if __name__ == '__main__':

    if len(sys.argv) not in [3,4]:
        sys.exit("Usage: " + "python " + sys.argv[0] + " exp_name" + " band" + " [ref-station]")

# band name - frequency mapping
# TODO: add regexp for frequencies
    login = os.getlogin()
    freq_dict = {"l": "166", "c": "48", "k": "22"}
    logs_dir = '/home/difxmgr/exper/'
    #exp_name = 'raes03jv'
    exp_name = sys.argv[1]
    #band = 'l'
    band = sys.argv[2]
    #refant = 'EFLSBERG'
    try:
        refant = sys.argv[3]
    except IndexError:
	refant = "EFLSBERG"

# Creating experiment directory
    os.chdir('/data/' + login + '/VLBI/pima/')
    try:
        os.mkdir(exp_name)
    except OSError:
    	sys.exit("Directory /data/" + login + "/VLBI/pima/" + str(exp_name) + " already exists!")

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
    check_fits_file(exp_name, band, exp_dir, logs_dir)

# Finding out number of scans:
    #os.chdir("/data/ilya/pima_scr/")
    #text = open(exp_name + "_" + band + ".obs")
    #number_of_scans = len(re.findall("#SCA", text.read()))
    #os.chdir(exp_dir)

# PROCEEDING WITH PIMA

# Loading fits-files
    print("loading fits-files... ")
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band load'")

    print("loading ephemerids... ")
    os.system("tcsh -c get_orbitfile.sh '$exp_name'")

# Coarse fringe-fitting
    print("coarse fring-fitting... ")
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band coarse'")

# Bandpass calibration
    print("bandpass calibration... ")
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band bpass'")

# Fine fringe-fitting and parsing for SNR values
    print("fine fringe-fitting... ")
    fname = exp_name + "_" + band + "_fine.log"
    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: RR'")

    RR = find_kths_words_in_file(fname, [-1,-4], ["SNR=", refant, "RADIO-AS"])

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: LL'")
    LL = find_kths_words_in_file(fname, [-1,-4], ["SNR=", refant, "RADIO-AS"])

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: RL'")
    RL = find_kths_words_in_file(fname, [-1,-4], ["SNR=", refant, "RADIO-AS"])

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: LR'")
    LR = find_kths_words_in_file(fname, [-1,-4], ["SNR=", refant, "RADIO-AS"])

    print("====================================")
    print("Results (RR, LL, RL, LR) :")
    for i in range(len(RR)):
        print("#" + str(i + 1) + ":")
	print("baseline " + str(RR[i][1]))
	print(RR[i][0], LL[i][0], RL[i][0], LR[i][0])
	print("====================================")
