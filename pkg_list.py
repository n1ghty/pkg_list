## pkg_list v1.00 by n1ghty
##
## This file is based on
## UnPKG rev 0x00000008 (public edition), (c) flatz
## and
## Python SFO Parser by: Chris Kreager a.k.a LanThief

import sys, os, struct, traceback, csv
import xlsxwriter

## parse arguments
if len(sys.argv) < 2:
	script_file_name = os.path.split(sys.argv[0])[1]
	print 'usage: {0} <pkg paths>'.format(script_file_name)
	sys.exit()

pkg_paths = []

for path in sys.argv[1:]:
	pkg_paths.append(path)
	if not os.path.isdir(path):
		print 'ERROR: invalid path specified'
		sys.exit()


## utility functions

def convert_bytes(num):
	"""
	this function will convert bytes to MB.... GB... etc
	"""
	for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
		if num < 1024.0:
			return "%3.1f %s" % (num, x)
		num /= 1024.0


def read_string(f, length):
	return f.read(length)
def read_cstring(f):
	s = ''
	while True:
		c = f.read(1)
		if not c:
			return False
		if ord(c) == 0:
			break
		s += c
	return s

def read_uint32_be(f):
	return struct.unpack('>I', f.read(struct.calcsize('>I')))[0]

def str2hex(s, size=8):
	"String converter to hex"
	if (len(s) * size) <= 32:
		h = 0x0
	else:
		h = 0x0L
	for c in s:
		h = (h << size) | ord(c)
	return h


def hex2hexList(h, size=8, reverse=True):
	"hex converter to hex list"
	return hex2hexList_charList(h, size, reverse, False)


def hex2hexList_charList(h, size=8, reverse=True, ischr=True):
	"hex converter to either chr list or hex list"
	l = []
	if h == 0x0:
		if ischr:
			l.append(chr(h))
		else:
			l.append(h)
		return l
	while h:
		_h = (h & mask_bit(size))
		if ischr:
			horc = chr(_h)
		else:
			horc = _h
		l.append(horc)
		h = (h >> size)
	if reverse: l.reverse()
	return l


def str2hexList(s, size=8, reverse=True):
	"String converter to hex list"
	return hex2hexList(str2hex(s), size, reverse)


def mask_bit(size=8):
	if size > 32:
		return (0x1L << size) - (0x1)
	else:
		return (0x1 << size) - (0x1)

def le32(bits):
	bytes = str2hexList(bits)
	result = 0x0
	offset = 0
	for byte in bytes:
		result |= byte << offset
		offset += 8
	return result



def le16(bits):
	bytes = str2hexList(bits)
	if len(bytes) > 1:
		return (bytes[0] | bytes[1] << 8)
	return (bytes[0] | 0x0 << 8)


class PsfHdr:
	size = 20

	def __init__(self, bits):
		self.size = 20
		self.data = bits[:self.size]
		self.magic = str2hexList(bits[:4])
		self.rfu000 = str2hexList(bits[4:8])
		self.label_ptr = bits[8:12]
		self.data_ptr = bits[12:16]
		self.nsects = bits[16:20]

	def __len__(self):
		return self.size


class PsfSec:
	size = 16

	def __init__(self, bits):
		self.size = 16
		self.data = bits[:self.size]
		self.label_off = bits[:2]
		self.rfu001 = bits[2:3]
		self.data_type = str2hex(bits[3:4])  # string=2, integer=4, binary=0
		self.datafield_used = bits[4:8]
		self.datafield_size = bits[8:12]
		self.data_off = bits[12:16]

	def __len__(self):
		return self.size

# main code
PsfMagic = "\0PSF"
PKG_MAGIC = '\x7FCNT'
CONTENT_ID_SIZE = 0x24
APP_VER_SIZE = 0x05
VERSION_SIZE = 0x05
list_file = "pkg_list.xlsx"

class MyError(Exception):
	def __init__(self, message):
		self.message = message

	def __str__(self):
		return repr(self.message)

class FileTableEntry:
	entry_fmt = '>IIIIII8x'

	def __init__(self):
		pass

	def read(self, f):
		self.type, self.unk1, self.flags1, self.flags2, self.offset, self.size = struct.unpack(self.entry_fmt, f.read(struct.calcsize(self.entry_fmt)))
		self.key_index = (self.flags2 & 0xF000) >> 12
		self.name = None

def getPkgInfo(pkg_file_path):
	try:
		with open(pkg_file_path, 'rb') as pkg_file:
			magic = read_string(pkg_file, 4)
			if magic != PKG_MAGIC:
				raise MyError('invalid file magic')

			pkg_file.seek(0x10)
			num_table_entries = read_uint32_be(pkg_file)

			pkg_file.seek(0x18)
			file_table_offset = read_uint32_be(pkg_file)

			#pkg content id may be used for extended formatting
			#pkg_file.seek(0x40)
			#content_id = read_cstring(pkg_file)
			#if len(content_id) != CONTENT_ID_SIZE:
			#	raise MyError('invalid content id')

			table_entries = []
			table_entries_map = {}
			pkg_file.seek(file_table_offset)
			for i in xrange(num_table_entries):
				entry = FileTableEntry()
				entry.read(pkg_file)
				table_entries_map[entry.type] = len(table_entries)
				table_entries.append(entry)

			for i in xrange(num_table_entries):
				entry = table_entries[i]
				if entry.type == 0x1000:
					pkg_file.seek(entry.offset)
					data = pkg_file.read(entry.size)
					if not data.find(PsfMagic) == 0:
						raise MyError("param.sfo is not a PSF file ! [PSF Magic == 0x%08X]\n" % str2hex(PsfMagic))

					psfheader = PsfHdr(data)
					psfsections = PsfSec(data[PsfHdr.size:])
					psflabels = data[le32(psfheader.label_ptr):]
					psfdata = data[le32(psfheader.data_ptr):]

					index = PsfHdr.size
					sect = psfsections

					for i in xrange(0, le32(psfheader.nsects)):
						le16(sect.label_off), le32(sect.data_off),
						le32(sect.datafield_size),
						le32(sect.datafield_used), sect.data_type,
						str2hex(sect.rfu001),
						if psflabels[le16(sect.label_off):].split('\x00')[0] == "TITLE":
							TITLE = psfdata[le32(sect.data_off):].split('\x00\x00')[0]
						if psflabels[le16(sect.label_off):].split('\x00')[0] == "CONTENT_ID":
							CONTENT_ID = psfdata[le32(sect.data_off):].split('\x00\x00')[0]
							if len(CONTENT_ID) != CONTENT_ID_SIZE:
								raise MyError('parsing of param.sfo failed. Invalid content_id length.')
						if psflabels[le16(sect.label_off):].split('\x00')[0] == "TITLE_ID":
							TITLE_ID = psfdata[le32(sect.data_off):].split('\x00\x00')[0]
						if psflabels[le16(sect.label_off):].split('\x00')[0] == "VERSION":
							VERSION = psfdata[le32(sect.data_off):].split('\x00\x00')[0]
							if len(VERSION) != VERSION_SIZE:
								raise MyError('parsing of param.sfo failed. Invalid version length.')
						if psflabels[le16(sect.label_off):].split('\x00')[0] == "APP_VER":
							APP_VER = psfdata[le32(sect.data_off):].split('\x00\x00')[0]
							if len(APP_VER) != APP_VER_SIZE:
								raise MyError('parsing of param.sfo failed. Invalid app_ver length.')
						index += PsfSec.size
						sect = PsfSec(data[index:])

					if CONTENT_ID and VERSION and APP_VER:
						NEW_FILENAME = "{0}-A{1}-V{2}.pkg".format(CONTENT_ID, APP_VER.replace(".",""), VERSION.replace(".",""))
					else:
						raise MyError('parsing of param.sfo failed')
					break

			## may be used for extended formatting
			#is_digests_valid = computed_main_entries1_digest == main_entries1_digest
			#is_digests_valid = is_digests_valid and computed_main_entries2_digest == main_entries2_digest
			#is_digests_valid = is_digests_valid and computed_digest_table_digest == digest_table_digest
			#is_digests_valid = is_digests_valid and computed_body_digest == body_digest
			#is_digests_valid = is_digests_valid and computed_entry_digests == entry_digests

			# get filesize
			pkg_file.seek(0, os.SEEK_END)
			size = convert_bytes(pkg_file.tell())
			pkg_file.close()

			update = (APP_VER != '01.00')
			if (CONTENT_ID[0] == 'E'):
				region = 'EU'
			elif (CONTENT_ID[0] == 'U'):
				region = 'US'
			elif (CONTENT_ID[0] == 'H'):
				region = 'CN'
			else:
				region = 'UNKNOWN'
			return {'TITLE' : TITLE, 'TITLE_ID' : TITLE_ID, 'VERSION' : VERSION, 'APP_VER' : APP_VER, 'CONTENT_ID' : CONTENT_ID, 'isUpdate' : update, 'REGION' : region, 'SIZE' : size}
	except IOError:
		print 'ERROR: i/o error during processing'
	except MyError as e:
		print 'ERROR:', e.message
	except:
		print 'ERROR: unexpected error:', sys.exc_info()[0]
		traceback.print_exc(file=sys.stdout)

def getReadableString(s):
	try:
		s_u = s.decode('utf-8')
	except:
		s_u = s
	return s_u

count = 0
count_err = 0
count_app = 0
count_upd = 0

workbook = xlsxwriter.Workbook(list_file)
worksheet_app = workbook.add_worksheet('Applications')
worksheet_upd = workbook.add_worksheet('Updates')
worksheet_err = workbook.add_worksheet('Failures')

fieldnames = ['TITLE', 'TITLE_ID', 'REGION', 'VERSION', 'APP_VER', 'CONTENT_ID', 'SIZE']

for pkg_path in pkg_paths:
	for root, directories, files in os.walk(pkg_path):
		for file in files: 
			if file.lower().endswith(".pkg"):
				count += 1
				try:
					pkgInfo = getPkgInfo(os.path.join(root, file))
					# set worksheet
					if pkgInfo['isUpdate']:
						sheet = worksheet_upd
						count_upd += 1
						count_sheet = count_upd
					else:
						sheet = worksheet_app
						count_app += 1
						count_sheet = count_app
					# fill row
					for pos in range(len(fieldnames)):
						if (fieldnames[pos] == 'TITLE'):
							sheet.write(count_sheet, pos, getReadableString(pkgInfo[fieldnames[pos]]))
						else:
							sheet.write(count_sheet, pos, pkgInfo[fieldnames[pos]])
				except:
					# failed to parse pkg
					count_err +=1
					worksheet_err.write(count_err, 0, file)

# prepare header
header = []
for pos in range(len(fieldnames)):
	header.append({'header': fieldnames[pos]})

worksheet_app.add_table(0, 0, (count_app if (count_app > 0) else 1), len(fieldnames)-1, {'style': 'Table Style Medium 8', 'columns' : header})
worksheet_upd.add_table(0, 0, (count_upd if (count_upd > 0) else 1), len(fieldnames)-1, {'style': 'Table Style Medium 8', 'columns' : header})
for sheet in (worksheet_app, worksheet_upd):
	sheet.set_column(0, 0, 62)  # TITLE width
	sheet.set_column(1, 1, 10)  # TITLE_ID width
	sheet.set_column(2, 2, 9)  # REGION width
	sheet.set_column(3, 3, 10)  # VERSION width
	sheet.set_column(4, 4, 10)  # APP_VER width
	sheet.set_column(5, 5, 42)  # CONTENT_ID width
	sheet.set_column(6, 6, 10)  # SIZE width
worksheet_err.add_table(0, 0, (count_err if (count_err > 0) else 1), 0, {'style': 'Table Style Medium 8', 'columns' : [{'header' : 'Filename'}]})
worksheet_err.set_column(0, 0, 80)  # filename width

try:
	workbook.close()
except:
	print 'ERROR: unable to write to file', list_file
	sys.exit()
print "Saved list of {0} pkg files to {1}".format(count, list_file)
print
print "Found:"
print "{0} Applications".format(count_app)
print "{0} Updates".format(count_upd)
print "{0} PKG files failed to parse".format(count_err)
