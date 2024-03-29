from __future__ import print_function
import os
import re
import sys
import glob
import fileinput
import paramiko
import argparse


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
        if line.startswith(start):
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


def get_files(names, host, port, username, password, remote_path):
    """
    Get files with name containing ``names`` from remote host to local
    directory.
    """

    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    sftp.chdir(remote_path)
    files = sftp.listdir()
    got_files = list()

    for fname in files:
        file_to_get = find_kth_word_in_line(fname, 0, names)
        if file_to_get:
            print("Downloading " + file_to_get + " from " + host + ":" +
            remote_path + "/")
            sftp.get(file_to_get, file_to_get)
            print("Done Downloading")
            got_files.append(file_to_get)

    return got_files


def find_fnames_in_files(pattern, files):
    """
    Find file names with pattern in files. Eg. find FITS-files with the desired
    band from log-files.

    Input:
        pattern - [str] - pattern in file name
	files - [container of str] - files to parse
    Output:
        [list of file name]
    """

    found_files = set()
    for one_file in files:
        with open(one_file) as lf:
            for line in lf.readlines():
                if pattern in line:
                    file_ = one_file.rstrip(".log")
                    file_ += ".FITS"
                    found_files.add(one_file)
   
    return found_files


def add_line_after_line_in_file(line_to_add, line_contains, fname, start=''):
    """
    Add specified line after some line in specified file. Eg. add record after
    previously commented record with UV_FITS.
    """

    add_after_line = False
    for line in fileinput.input(fname, inplace=1):
        print(line.strip())
	if line_contains in line and line.startswith(start):
            add_after_line = True
        if not (line_contains in line and line.startswith(start)) and add_after_line:
            add_after_line = False
            print(line_to_add.strip())


def check_fits_file(exp_name, band, exp_dir, logs_dir=None):
    """
    Builds list of FITS-files on the basis of logs and adds them to *.cnt-file.
    If no files with specified band are found in logs_dir => throws
    NoUVFilesException.
    """

    print('In check_fits_file with:')
    print('expname: ' + str(exp_name))
    print('band: ' + str(band))
    if logs_dir:
        print('exp_dir: ' + str(exp_dir))
        print('logs_dir: ' +str(logs_dir))
        # Find FITS-files with the desired band from logs
        logs_directory = logs_dir + exp_name
        logs_files = glob.glob(logs_directory + "/*.log")

        files_to_add = find_fnames_in_files("Freq=" + freq_dict[band], logs_files)
        files_to_add = [file_.rstrip(".log") for file_ in files_to_add]
        files_to_add = [file_ + ".FITS" for file_ in files_to_add]

    else:
        files_to_add = None

    # If we haven't found fits-files in logs then look for them in
    # archive
    if not files_to_add:
        print("No FITS-files are found in local logs.")
        print("Searching in archive.asc.rssi.ru")
	files_to_add = get_files(['_' + str(band).upper() + '_', 'fits'], host, port,
		username, password, remote_path)
    if not files_to_add:
	    raise NoUVFilesException("No FITS-files found nor in local logs not in archive.asc.rssi.ru of " + str(exp_name))

    print("Found files: ")
    print(files_to_add)

    cnt_file = glob.glob(exp_dir + "/*.cnt")[0]
    print("cnt-file is: " + cnt_file)


    # Comment out previous UV_FITS blocks in *.cnt-file
    replace(cnt_file, "UV_FITS:", "#UV_FITS:")

    # Add record after previously commented record with UV_FITS
    for fits_file in files_to_add:
        line = "UV_FITS:            " + fits_file
	add_line_after_line_in_file(line, '', cnt_file, start='#UV_FITS:')
   

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    #parser.add_argument('-a', action='store_true', default=False,
    #dest='use_archive_ftp', help='Use archive.asc.rssi.ru ftp-server for\
    #FITS-files')

    parser.add_argument('-asc', action='store_const', dest='remote_dir',
    const='/', help='Download asc-correlator FITS-files')

    parser.add_argument('-difx', action='store_const', dest='remote_dir',
    const='/quasars_difx', help='Download difx-correlator FITS-files')

    parser.add_argument('exp_name', type=str, help='Name of the experiment')
    parser.add_argument('band', type=str, help='Frequency [c,k,l,p]')
    parser.add_argument('refant', type=str, default='EFLSBERG', help='Ground antenna', nargs='?')

    args = parser.parse_args()

   # if not args.remote_dir:
   #     sys.exit("Use -asc/-difx flags to select archive's fits-files")
    	


    # paramiko setup
    # TODO: add to names
    names = ['.fits', '.idifits']
    host = "archive.asc.rssi.ru"
    port = 22
    username = "quasars"
    password = "JcSzi5_k"
    # if using asc or difx FITS-files - remote_dir contains arg
    if args.remote_dir:
        remote_path = args.remote_dir + args.exp_name

    login = os.getlogin()
    freq_dict = {"l": "166", "c": "48", "k": "22"}
    logs_dir = '/home/difxmgr/exper/'
    exp_name = args.exp_name
    band = args.band
    try:
        refant = args.refant
    except AttributeError:
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
    os.environ['refant'] = refant

    # Creating .cnt-file for our experiment
    os.system("tcsh -c 'new_cnt.sh $exp_name $band'")

    # Replacing default reference antenna and allowing for bandpass
    # calibration.
    replace(glob.glob(exp_dir + "/*.cnt")[0], 'EFLSBERG', refant)
    replace(glob.glob(exp_dir + "/*.cnt")[0], 'BANDPASS_FILE:      NO # ', 'BANDPASS_FILE:      ')

    # Inserting FITS-files with the desired band found in logs to *.cnt-file
    # and commenting out previous entries. 
    if args.remote_dir:
        check_fits_file(exp_name, band, exp_dir, logs_dir=None)
    else:
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

    RR = find_kths_words_in_file(fname, [-1, -4], ["SNR=", refant, "RADIO-AS"])

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: LL'")
    LL = find_kths_words_in_file(fname, [-1, -4], ["SNR=", refant, "RADIO-AS"])

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: RL'")
    RL = find_kths_words_in_file(fname, [-1, -4], ["SNR=", refant, "RADIO-AS"])

    os.system("tcsh -c 'pima_fringe.csh $exp_name $band fine POLAR: LR'")
    LR = find_kths_words_in_file(fname, [-1, -4], ["SNR=", refant, "RADIO-AS"])

    print("Debug")
    print(RR)
    print(LL)
    print(RL)
    print(LR)
    print("Debug")

    print("====================================")
    print("Results (RR, LL, RL, LR) :")
    for i in range(len(RR)):
        print("#" + str(i + 1) + ":")
	print("baseline " + str(RR[i][1]))
        print(RR[i][0], LL[i][0], RL[i][0], LR[i][0])
        print("====================================")
