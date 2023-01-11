import argparse 
import utils

"""
 FolderCleanup - Script to clean up folders/files that are over X days old
"""
parser = argparse.ArgumentParser(
	prog = 'FolderCleanup',
	description = 'Script to clean up folders/files that are over X days')

parser.add_argument('-p', '--path', 
	required=True, 
	help='Specifies the target path to clean up.')
	
parser.add_argument('-a', '--age', 
	required=True, 
	help='Specifies the target Age in days, e.g. Last write time of the item.')

parser.add_argument('-f', '--force', 
	action='store_true',
	required=False, 
	help='Parameter that allows for hidden and read-only files to be removed.')

parser.add_argument('-e', '--emptyfolder', 
	action='store_true',
	required=False, 
	help='Remove empty folders.')

args = parser.parse_args()

print(f'Path: {args.path}, Age: {args.age}, Force: {args.force}, EmptyFolder: {args.emptyfolder}')

def run(path, age, force, emptyFolder):
	folders = utils.get_folders(path)
	begin_stats = utils.get_diskusage(path)

	results = 0
	for folder in folders:
		results = results + utils.remove_ageditems(folder, age, force, emptyFolder)
	
	print(f'Removed {results} files from {path} older than {age} days')
	end_stats = utils.get_diskusage(path)
	print (f'Begin: {begin_stats}')
	print (f'End: {end_stats}')
	print (f'Space freed up: Start: {utils.format_filesize(begin_stats.free)}, End: {utils.format_filesize(end_stats.free)}, Total: {utils.format_filesize(end_stats.free - begin_stats.free)}')

if __name__ == "__main__":
	run(args.path, args.age, args.force, args.emptyfolder)