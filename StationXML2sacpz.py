#!/bin/python3

import sys
import os.path
import glob
import time
import xml.etree.ElementTree as et

if len(sys.argv) ==1:
	print(sys.argv[0], "-h or --h[elp] for help message\n", file=sys.stderr);
	sys.exit();

# in case of help message
if sys.argv[1] == "-h" or sys.argv[1] == "--h" or sys.argv[1] == "--help":
	print("\nUsage:", sys.argv[0],"(xml files) [-o (output directory)] -m (metafile name) \n\n\
	-h, --h, --help: show help message and exit\n\
	-o             : output directory to save SACPZ files \n\n\
	We will overwrite all the pre existing files with the same name.\n\
	If we have many station-location-channel pairs with different dates in the input xml files,\n\
	those are all printed as different file with dates appended.\n\
	ver 202003062100\n", file=sys.stderr);
	sys.exit();

# we can take multiple input xml file.
ns = {'ns0':'http://www.fdsn.org/xml/station/1'};
xmllist = [];
outputdir = ".";
metafile = "";

i = 1;
while i < len(sys.argv):
	if sys.argv[i]=='-o':
		i = i + 1;
		outputdir = sys.argv[i];
	elif sys.argv[i] == '-m':
		i = i + 1;
		metafile = sys.argv[i];
	else:
		# check the existence first
		if os.path.isfile(sys.argv[i]) == True:
			xmllist.append(sys.argv[i]);
		else:
			print("file not existing: ", sys.argv[i], file = sys.stderr);

	i += 1;

# we save the log file.
logfile = open("%s/filelog.txt" %(outputdir), 'w+');

# if we still have metafile as "", that is NG.
if metafile == "":
	print("meta file should be put in with '-m' \n", file=sys.stderr);
	sys.exit();

# open the meta file to write.
fmeta = open(metafile, 'w');
fmeta.write('#net,sta,loc,chan,lat,lon,elev,depth,azimuth,SACdip,instrument,scale,scalefreq,scaleunits,samplerate,start,end\n');

# check the SACPZ file pre existing;
pre_sacpzfiles = glob.glob("%s/SACPZ.*" %(outputdir));
pre_sacpzfiles_ind = [];
for presacpzfile in pre_sacpzfiles:
	pre_sacpzfiles_ind.append(0);

for xmlfile in xmllist:
	sxml = et.parse(xmlfile);
	ssxml = sxml.getroot();

	for network in ssxml.findall('ns0:Network', ns):
		network_a = network.attrib;
		networkname = network_a['code'];
		for station in network.findall('ns0:Station', ns):
			station_a = station.attrib;
			staname = station_a['code'];
			# location info
			stla = float(station.find('ns0:Latitude', ns).text);
			stlo = float(station.find('ns0:Longitude', ns).text);
			stel = float(station.find('ns0:Elevation', ns).text); 
			for channel in station.findall('ns0:Channel', ns):
				channel_a = channel.attrib;
				chname = channel_a['code'];
				loc = channel_a['locationCode'];
				sdate = channel_a['startDate'];
				edate = channel_a['endDate'];

				# the location informations
				chdp = float(channel.find('ns0:Depth', ns).text);
				chaz = float(channel.find('ns0:Azimuth', ns).text);
				chdip = float(channel.find('ns0:Dip', ns).text);
				samplerate = float(channel.find('ns0:SampleRate', ns).text);
			
				sensor_model = "";
				if channel.find('ns0:Sensor', ns).find('ns0:Model', ns) != None:
					sensor_model = channel.find('ns0:Sensor', ns).find('ns0:Model', ns).text;
				elif channel.find('ns0:Sensor', ns).find('ns0:Type', ns) != None:
					sensor_model = channel.find('ns0:Sensor', ns).find('ns0:Type', ns).text;
				else:
					print("no sensor_model confirmed??\b", file=sys.stderr);

				resp = channel.find('ns0:Response', ns);
				sensitivity = float(resp.find('ns0:InstrumentSensitivity', ns).find('ns0:Value', ns).text);
				sensitivity_f = float(resp.find('ns0:InstrumentSensitivity', ns).find('ns0:Frequency', ns).text);

				input_unit = resp.find('ns0:InstrumentSensitivity', ns).find('ns0:InputUnits', ns).find('ns0:Name', ns).text;
				input_unit_exp = resp.find('ns0:InstrumentSensitivity', ns).find('ns0:InputUnits', ns).find('ns0:Description', ns).text;

				output_unit = resp.find('ns0:InstrumentSensitivity', ns).find('ns0:OutputUnits', ns).find('ns0:Name', ns).text;
				output_unit_exp = resp.find('ns0:InstrumentSensitivity', ns).find('ns0:OutputUnits', ns).find('ns0:Description', ns).text;
				# now on to the response 
				ipz = 0;
				A0 = 1; A0_freq = 0;
				inputunit = ""; outputunit = "";
				instgain = 1;
				poles_r = []; poles_i = [];
				zeros_r = []; zeros_i = [];
				for stage in resp.findall('ns0:Stage', ns):
					# we take poles and zeros only once.
					poleszeros = stage.findall('ns0:PolesZeros', ns);
					if len(poleszeros)==1 and ipz ==0:
						ipz = 1;
						polezero = poleszeros[0];
						#inputunit = polezero.find('ns0:InputUnits', ns).find('ns0:Name', ns).text;
						#outputunit = polezero.find('ns0:OutputUnits', ns).find('ns0:Name', ns).text;
						A0 = float(polezero.find('ns0:NormalizationFactor', ns).text);
						A0_freq = float(polezero.find('ns0:NormalizationFrequency', ns).text);

						for zero in polezero.findall('ns0:Zero', ns):
							zeros_r.append(float(zero.find('ns0:Real', ns).text));
							zeros_i.append(float(zero.find('ns0:Imaginary', ns).text));

						for pole in polezero.findall('ns0:Pole', ns):
							poles_r.append(float(pole.find('ns0:Real', ns).text));
							poles_i.append(float(pole.find('ns0:Imaginary', ns).text));
						instgain = float(stage.find('ns0:StageGain', ns).find('ns0:Value', ns).text);
						
					elif len(poleszeros)==1 and ipz==1:
						print("something wrong in the file or the algorithm??\n", file=sys.stderr);
						sys.exit();

					# for the change of V to digital counts is not needed.

				# now print this channel as a file. example name: SACPZ.IU.ANMO.00.BH1
				pzname = "%s/SACPZ.%s.%s.%s.%s" % (outputdir, networkname, staname, loc, chname);
				iprevious = 0;
				if os.path.isfile(pzname) == True:
					for i in range(0, len(pre_sacpzfiles)):
						if pzname == pre_sacpzfiles[i]:
							iprevious = 1;
							pre_sacpzfiles_ind[i] = 1;
							
					if iprevious ==0:
						pzname = "%s/SACPZ.%s.%s.%s.%s_S%s_E%s" % (outputdir, networkname, staname, loc, chname, sdate, edate);

				# now write as a file
				fsacpz = open(pzname, 'w');
				localcomps = time.asctime( time.localtime(time.time()) ).split(" ");
				# example: ['Sat', 'Mar', '', '7', '14:54:08', '2020']
				month="";
				if localcomps[1] == "Jan":
					month = "01";
				elif localcomps[1] == "Feb":
					month = "02";
				elif localcomps[1] == "Mar":
					month = "03";
				elif localcomps[1] == "Apr":
					month = "04";
				elif localcomps[1] == "May":
					month = "05";
				elif localcomps[1] == "Jun":
					month = "06";
				elif localcomps[1] == "Jul":
					month = "07";
				elif localcomps[1] == "Aug":
					month = "08";
				elif localcomps[1] == "Sep":
					month = "09";
				elif localcomps[1] == "Oct":
					month = "10";
				elif localcomps[1] == "Nov":
					month = "11";
				elif localcomps[1] == "Dec":
					month = "12";
				else:
					print("error in the algorithm...?\n", file=sys.stderr);
					sys.exit();

				localtime = "%s-%s-%sT%s" %(localcomps[-1], month, localcomps[-3], localcomps[-2]);
				Constant = A0*sensitivity;

				# write the basic informations first
				fsacpz.write('* **********************************\n');
				fsacpz.write('* NETWORK (KNETWK): %s              \n' %(networkname));
				fsacpz.write('* STATION  (KSTNM): %s              \n' %(staname));
				fsacpz.write('* LOCATION (KHOLE): %s              \n' %(loc));
				fsacpz.write('* CHANNEL (KCMPNM): %s              \n' %(chname));
				fsacpz.write('* CREATED         : %s              \n' %(localtime));
				fsacpz.write('* START           : %s              \n' %(sdate));
				fsacpz.write('* END             : %s              \n' %(edate));
				fsacpz.write('* DESCRIPTION     :                 \n');
				fsacpz.write('* LATITUDE        : %.6f            \n' %(stla));
				fsacpz.write('* LONGITUDE       : %.6f            \n' %(stlo));
				fsacpz.write('* ELEVATION       : %f              \n' %(stel));
				fsacpz.write('* DEPTH           : %.2f            \n' %(chdp));
				fsacpz.write('* DIP             : %.1f            \n' %(chdip));
				fsacpz.write('* AZIMUTH         : %.1f            \n' %(chaz));
				fsacpz.write('* SAMPLE RATE     : %f              \n' %(samplerate));
				fsacpz.write('* INPUT UNIT      : %s              \n' %(input_unit));
				fsacpz.write('* OUTPUT UNIT     : %s              \n' %(output_unit));
				fsacpz.write('* INSTTYPE        : %s              \n' %(sensor_model));
				fsacpz.write('* INTSGAIN        : %.6e              \n' %(instgain));
				fsacpz.write('* COMMENT         :                 \n');
				fsacpz.write('* SENSITIVITY     : %.6e              \n' %(sensitivity));
				fsacpz.write('* A0              : %.6e              \n' %(A0));
				fsacpz.write('* **********************************\n');
				fsacpz.write('ZEROS %d                            \n' %(len(zeros_r)));
				for i in range(0, len(zeros_r)):
					fsacpz.write('\t %.6e  %.6e\n' %(zeros_r[i], zeros_i[i]));
				fsacpz.write('POLES %d                            \n' %(len(poles_r)));
				for i in range(0, len(poles_r)):
					fsacpz.write('\t %.6e  %.6e\n' %(poles_r[i], poles_i[i]));
				fsacpz.write('CONSTANT\t %.6e\n' %(Constant));
				fsacpz.close();
				
				print("wrote as ", pzname, file=sys.stderr);
				print(pzname, file=logfile);

				# we also record in the metafile.
				# the format of meta file
				# #net,sta,loc,chan,lat,lon,elev,depth,azimuth,SACdip,instrument,scale,scalefreq,scaleunits,samplerate,start,end
				#IU,ANMO,00,BH1,34.945981,-106.457133,1671,145,328,90,Geotech KS-54000,3456610000,0.02,M/S,20,2008-06-30T20:00:00,2599-12-31T23:59:59
				fmeta.write('%s,%s,%s,%s,%.6f,%.6f,%.2f,%.2f,%.1f,%.1f,%s,%d,%f,%s,%f,%s,%s\n' %(networkname, staname, loc, chname, stla, stlo, stel, chdp, chaz, chdip, sensor_model, int(sensitivity), sensitivity_f, input_unit, samplerate, sdate, edate));

	
fmeta.close();
logfile.close();
