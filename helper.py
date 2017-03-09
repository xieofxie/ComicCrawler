#! python3

import argparse,os

parser = argparse.ArgumentParser(description='helper for ComicCrawler in windows')
parser.add_argument('-p',help='set a python path if not using default one')
parser.add_argument('-d',action='store_true',help='install dependencies')

args = parser.parse_args()

pipStr = 'pip'
if args.p:
	pipStr = args.p + '/Scripts/' + pipStr

if args.d:
	os.system(pipStr + ' install -r requirements.txt')
else:
	ccStr = 'comiccrawler'
	if args.p:
		ccStr = args.p + '/Scripts/' + ccStr	
	os.system(pipStr + ' install -e .')
	os.system(ccStr + ' gui')
