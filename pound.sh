cd /media/sms-pool/smet_scraper
sleep $(( RANDOM \% 18000));
PYTHONPATH=/media/sms-pool/holly /usr/bin/python3 /media/sms-pool/smet_scraper/pound.py
