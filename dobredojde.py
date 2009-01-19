#!/usr/bin/python
# -*-: coding: utf-8 -*-

import lightblue
import time, pickle, datetime, os, random, sys, logging, logging.handlers, mimetypes

class DobredojdeBluetooth:
    """Добредојде на секој им посакува или ако веќе го знае му праќа случајна сликичка.
    Прима вредности:
        dir_so_sliki    - од каде да ги зима .jpg сликите што ќе ги праќа.
        vcard_fajl      - која vcf датотека да ја праќа.
        period          - колкав период да ги игнорира уредите што ги гледа повеќе пати.
        debug           - Дали да печати многу информации што праи.
        logot           - во која датотека да ги запишува информациите
    """

    def __init__(self,dir_so_sliki='sliki/',vcard_fajl='vcard.vcf',period=120,debug=True,logot='logs/dobredojde.log'):
        self.logot = logot
        logfajl = logging.handlers.RotatingFileHandler(logot,maxBytes=1048576,backupCount=10)
        if debug:
            logging.getLogger('').setLevel(logging.DEBUG)
        else:
            logging.getLogger('').setLevel(logging.INFO)
        logfajl_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logfajl.setFormatter(logfajl_format)
        logging.getLogger('').addHandler(logfajl)

        self.dir_so_sliki = dir_so_sliki
        self.vcard_fajl = vcard_fajl
        self.period = period
        self.vchitaj_videni()

    def vchitaj_videni(self):
        "Вчитај ги видените уреди"
        try:
            f = open('videni.pkl','rb')
            self.videni = pickle.load(f)
            f.close()
        except:
            logging.debug("Nekoj go izbrishal videni fajlot ili prvpat me pushtash.")
            self.videni = []

    def snimi_videni(self):
        "Сними ги видените уреди"
        try:
            f = open('videni.pkl','wb')
            pickle.dump(self.videni,f)
            f.close()
        except Exception, e:
            logging.error("Nemozham da zapisham vo videni fajlot. %s" % str(e))
            logging.error("Kje se izgubat site uredi koi gi vidov dodeka rabotev. Eve gi vo logov:")
            for ured in self.videni:
                logging.error("%s %s %s" % (ured['mac'],ured['ime'],str(ured['posleden_pat'])))
    
    def pechati_videni(self):
        "Ги прикажува видените уреди"
        for ured in self.videni:
            print "Ured: %s (%s). Viden: %s" % (ured['mac'],ured['ime'],str(ured['posleden_pat']))
    
    def dali_sum_go_videl(self,ured,sega):     
        "Во листата на videni уреди го барам ured и проверувам дали веќе сум го видел."
        for lokacija,viden in enumerate(self.videni):
            if ured[0]==viden['mac']:
                if datetime.timedelta(seconds=self.period)+viden['posleden_pat']>sega:
                    return True,lokacija #vekje sum go videl vo periodot i e na taa lokacija
                else:
                    return False,lokacija # vekje sum go videl ama bilo odamna i e na taa lokacija
        return False,-1 # prv pat go gleam uredov

    def random_slika(self):
        "Враќам случајна слика од фолдерот."
        fajl = ''
        while not fajl.endswith(".jpg"):
            fajl = random.choice(os.listdir(self.dir_so_sliki))
        return self.dir_so_sliki + fajl

    def prati_fajl(self,ured,vcard=False):
        """Го праќа фајлот преку Obex Object Push"""

        servisi = lightblue.findservices(addr=ured,servicetype=lightblue.OBEX)

        port = ''
        for servis in servisi:
            if servis[2]=='OBEX Object Push':
                port = servis[1]
                break

        if not port:
            logging.debug("Uredov %s nema OBEX Object push. Ne mu prativ nishto" % ured)
            return False # ako nema Obex Object push

        if vcard:
            fajl = self.vcard_fajl
        else:
            fajl = self.random_slika()
    

        client = lightblue.obex.OBEXClient(ured,port)
        fobj = file(fajl,'rb')
        headers = {"name":os.path.basename(fajl),
                    "length":os.stat(fajl).st_size,
                    "type":mimetypes.guess_type(fajl)[0]
                    }

        try:
            client.connect()
        
            # kolku sekundi da cheka dur prakja slikata nekoj da mu go odbie ili prifati
            client._OBEXClient__client.timeout=30 

            resp = client.put(headers,fobj)
            if resp.code != lightblue.obex.OK:
                raise lightblue.obex.OBEXError("Uredot me odbi")
        except lightblue.obex.OBEXError, e:
            logging.error("Ne uspeav da mu pratam na %s. Greshkata: %s" % (ured,str(e)))
        finally:
            fobj.close()
            try:
                client.disconnect()
            except:
                pass

    def kraj(self):
        "Заврши"
        self.snimi_videni()
        logging.info("Gotovo se gasam.")

    def run(self):
        logging.info("Pochnav da rabotam.")
        logging.debug("Periodot vo koj se praam naudren e %d chasa. (%d sekundi)" % (self.period / 3600, self.period))
        logging.debug("Slikite kje gi zimam od %s" % self.dir_so_sliki)
        logging.debug("Vcard fajlot e %s" % self.vcard_fajl)
        logging.debug("Logiram vo %s" % self.logot)
        try:
            while 1:
                sega = datetime.datetime.now()

                logging.debug("Baram bluetooth uredi...")
                najdeni = lightblue.finddevices()
        
                for najden in najdeni:
                    vekje_viden_deneska, na_lokacija = self.dali_sum_go_videl(najden,sega)

                    if na_lokacija==-1:
                        logging.info("Prvpat go gleam uredov: %s (%s), kje mu pratam vcard." % (najden[1],najden[0]))
                        self.videni.append({'mac':najden[0],'ime':najden[1],'posleden_pat':sega})
                        self.prati_fajl(najden[0], vcard=True)
                    else:
                        if vekje_viden_deneska:
                            logging.debug("Sum go videl vekje deneska %s (%s). Se praam naudren." % (najden[1],najden[0]))
                        else:
                            logging.debug("Sum go videl vekje uredov %s (%s), ama deneska prv pat pa kje mu pratam slikichka." % (najden[1],najden[0]))
                            self.videni[na_lokacija]={'mac':najden[0],'ime':najden[1],'posleden_pat':sega}
                            self.prati_fajl(najden[0], vcard=False)
                
                # pochekaj malku
                #logging.debug("Da ne preteruvam kje pochekam 30sekundi pred slednoto baranje.") 
                time.sleep(30)

        except KeyboardInterrupt:
            self.kraj()
    

###########

if __name__=='__main__':
    
    #Da logira i vo konzola
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logging.getLogger('').addHandler(console)
    
    s = DobredojdeBluetooth(debug=True,
                            period=21600, # 6 chasa
                            vcard_fajl='vcard.vcf',
                            dir_so_sliki='sliki/',
                            logot='logs/dobredojde.log')   
    #s.pechati_videni()
    s.run()
