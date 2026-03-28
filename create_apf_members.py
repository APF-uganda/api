"""
Script to create APF member accounts in the Django database.
Run inside the apf_backend Docker container:

    docker exec -it apf_backend python manage.py shell < create_apf_members.py

Or:
    docker exec -it apf_backend python create_apf_members.py
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

DEFAULT_PASSWORD = "Apf@uganda"

# Members from the APF register + Google Sheet data
# Format: (email, first_name, last_name, gender, membership_number, organization, job_title, icpau_reg_number, national_id)
MEMBERS = [
    ("kherman32@gmail.com", "Herman", "Karugaba", "male", "APF/M/008", "Peekay Steve Associates", "Practitioner", "FM2405", "CM890271069EEH"),
    ("patrickmugarura10@yahoo.com", "Patrick", "Mugarura", "male", "APF/M/009", "Pamu and Associates", "Managing partner", "FM2565", "CM8500910P8YVL"),
    ("gkkakala@gmail.com", "Godfrey", "Kakala", "male", "APF/M/010", "DATA HOUSE", "Partner", "FM401", "CM72067104L4CK"),
    ("constant.mayende@gmail.com", "Constant Othieno", "Mayende", "male", "APF/M/011", "CMK & CO", "Partner", "FM341", "CM73039101D2DH"),
    ("r.albert.otete@gmail.com", "Albert Richards", "Otete", "male", "APF/M/012", "J. SAMUEL RICHARDS & ASSOCIATES", "PARTNER", "FM131", "CM700381059MDF"),
    ("maria@springstugye.com", "Maria", "Nabbanja Ssentamu", "female", "APF/M/013", "Springs & Tugye Associates LLP", "Managing Partner", "FM396", "CF69024103RNCA"),
    ("nuwamanyageoffrey@gmail.com", "Geoffrey", "Nuwamanya", "male", "APF/M/014", "Greenfield & Company", "Managing Partner", "720", "21357558"),
    ("rmutumba@mutumbamukobe.org", "Ronald", "Mutumba", "male", "APF/M/004", "Mutumba Mukobe and Associates", "Managing Partner", "FM541", "CM71075100Y30F"),
    ("emojongodeke@gmail.com", "Joram", "Emojong-Odeke", "male", "APF/M/015", "FELBright & Co", "Managing Partner", "FM727", "CM65042101K3ZJ"),
    ("mante@continentalpartners.org", "David", "Nyende", "male", "APF/M/002", "CONTINENTAL PARTNERS", "PRINCIPAL PARTNER", "FM055", "CM480131091UJF"),
    ("justin@osillocpa.com", "Justin Keith", "Osillo", "male", "APF/M/016", "TGS Osillo", "Partner", "FM544", "CM81039103DAKF"),
    ("senogaassociates@gmail.com", "Abbey Ntege", "Senoga", "male", "APF/M/017", "SENOGA ASSOCIATES", "MANAGING DIRECTOR", "FM2190", "CM7705210459QD"),
    ("michael@springstugye.com", "Michael", "Tugyetwena", "male", "APF/M/005", "Springs and Tugye Associates LLP", "Partner", "FM1054", "CM81007102H7NA"),
    ("a.arnold@ardenfield.com", "Arnold", "Ahereza", "male", "APF/M/018", "ARDENFIELD CPA", "PARTNER", "FM792", "CM8202710GFOJH"),
    ("a.dennis@ardenfield.com", "Dennis", "Ahimbisibwe", "male", "APF/M/019", "ARDENFIELD CPA", "PARTNER", "FM779", ""),
    ("pius.ssuuna@gmail.com", "Pius Mawanda", "Ssuuna", "male", "APF/M/020", "Cartwright CPA", "Managing Partner", "FM613", "CM77100102PVAD"),
    ("rhodaochan@gmail.com", "Rhoda Kasinda", "Brenda", "female", "APF/M/021", "FBO Partners", "Audit Partner", "FM1036", "CF81036107QKHK"),
    ("annetnantumbwe1@gmail.com", "Annet", "Nantumbwe", "female", "APF/M/022", "Hill & Associates", "Partner", "116206", "CF8105210DX3QC"),
    ("ochanbernard@gmail.com", "Bernard Ochan", "Fred", "male", "APF/M/023", "FBO PARTNERS", "MANAGING PARTNER", "FM586", "CM67035104ETTK"),
    ("sekiziyivuissa@gmail.com", "Issa", "Sekiziyivu", "male", "APF/M/024", "ISSE AND ASSOCIATES", "MANAGING PRACTITIONER", "FM2148", ""),
    ("msilverboss@gmail.com", "Silver Boss", "Mwebesa", "male", "APF/M/007", "Ellie and Associates", "Managing Partner", "FM2406", "CM2004102QN8F"),
    ("muke280@gmail.com", "Hillary", "Mukebezi", "male", "APF/M/025", "HILL & ASSOCIATES", "PARTNER", "FM2889", ""),
    ("lmawanda45@gmail.com", "Lwanga", "Mawanda", "male", "APF/M/026", "mugabi & Mawanda Associates CPA", "PARTNER", "P0449", ""),
    ("kalindaassociates@gmail.com", "Gonzaga Joseph", "Kalinda", "male", "APF/M/006", "KALINDA & ASSOCIATES", "MANAGING DIRECTOR", "FM2333", "CM86082103P9ZG"),
    ("chrisnet4@gmail.com", "Christopher", "Kakande", "male", "APF/M/027", "KALINDA & ASSOCIATES", "PARTNER", "F3349", "CM840681026PKK"),
    ("info@pepartnersuganda.com", "Elnest Kalanzi", "Kato", "male", "APF/M/028", "Phillip & Elnest (PE) Partners", "Partner", "FM2518", "CM87012104VV4G"),
    ("jay.oriekot@gmail.com", "James", "Oriekot", "male", "APF/M/029", "Oriekot & Associates CPA", "CPA", "FM1451", "CM7403510529ZC"),
    ("rwomus.stepehn@gmail.com", "Stephen", "Rwomus", "male", "APF/M/030", "Rwos & Partners", "Sole Practitioner", "FM2678", "CM75034104P9GA"),
    ("annerozbob1@gmail.com", "Anne Rose", "Namatovu", "female", "APF/M/031", "SPRINGS AND TUGYE ASSOCIATES", "PARTNER", "fm1735", "CF74052102H8CE"),
    ("abdul@springstugye.com", "Abdul", "Mubiru", "male", "APF/M/032", "Springs & Tugye Associates LLP", "Partner", "715", "CM78099101JQRJ"),
    ("pkbanadda@gmail.com", "Paul Banadda", "Kiyingi", "male", "APF/M/033", "PAKS AND CO CPA", "Managing Partner", "FM440", "A00761693"),
    ("woodhask.ediomu@woodhask.com", "Ceaser Woodhask", "Ediomu", "male", "APF/M/034", "Woodhask Certified Public Accountants", "Partner", "FM3900", "CM92058101PFQH"),
    ("biz.bizandcompany@gmail.com", "James Buhiire Kwera", "Kamanyire", "male", "APF/M/035", "BIZ & CO. Certified Public Accountants", "Managing Partner", "FM157", "CM670461034VLG"),
    ("glutwama@gmail.com", "Godfrey", "Lutwama", "male", "APF/M/036", "Lutwama Associates CPA", "Practitioner", "FM 1497", "CM72032106C4HD"),
    ("dssebugwawo@gmail.com", "Dennis", "Ssebugwawo", "male", "APF/M/037", "Seden Associates, CPA", "Managing Partner", "FM3916", "CM910321034XAD"),
    ("arch.archelia@gmail.com", "Elias", "Kabenge", "male", "APF/M/038", "ARCHELIA", "Team Leader", "FM915", "CM720121068GLK"),
    ("kabuchualfred@gmail.com", "Alfred Beitwababo", "Kabuchu", "male", "APF/M/039", "BIZ & CO. Certified Public Accountants", "Partner", "FM223", "CM6900910J7KFF"),
    ("jbmwanja@gmail.com", "Joseph Byekwaso", "Mwanja", "male", "APF/M/040", "BIZ & CO. Certified Public Accountants", "Partner", "FM208", "CM60075105GFKL"),
    ("gadzk@yahoo.com", "Gad Zikehemura", "Tusiimire", "male", "APF/M/041", "Tezam &Co. CPA", "Partner", "FM920", "CM770371017L4k"),
    ("otimotile@yahoo.com", "Tom Otile", "Otim", "male", "APF/M/042", "PO 1034", "Practitioner", "FM 674", "CA030671399"),
    ("rmatsiko89@gmail.com", "Rollings", "Nyesigomwe", "male", "APF/M/043", "Ronye Associates", "Managing Partner", "FM3048", "CM89009103AZPK"),
    ("davidssenoga@gmail.com", "David", "Ssenoga", "male", "APF/M/044", "SDS&COMPANY", "PRACTITIONER", "529", "CM640991012RPF"),
    ("bwireb@gmail.com", "Benard", "Bwire W", "male", "APF/M/045", "BNB Associates LLP", "Managing Partner", "FM1954", "CM82042107FZGF"),
    ("thomsonkwizina@gmail.com", "Thomson", "Kwizina", "male", "APF/M/046", "TOMSON & Co.", "Managing Partner/CEO", "101208", "CM64018109C3HG"),
    ("mwagodassociates@gmail.com", "Godfrey", "Mwanguhya", "male", "APF/M/047", "MWAGOD ASSOCIATES", "Practitioner", "FM992", "CM700101043PJH"),
    ("jamiekasule@yahoo.com", "Jamilah", "Nankumbi", "female", "APF/M/048", "Janan Partners CPA", "Partner", "FM 1978", "CF80052107KFHD"),
    ("peterkasango1@gmail.com", "Peter", "Kasango", "male", "APF/M/049", "KAL ASSOCIATES", "MANAGING PARTNER", "100880", "1718010"),
    ("marknsubugacpa@gmail.com", "Mark Nagenda", "Nsubuga", "male", "APF/M/050", "AF0164", "Practitioner", "FM60", "CM8403610AHYXA"),
    ("rwebishugi@gmail.com", "David Rwebishugi", "Mugisha", "male", "APF/M/051", "Goldgate", "Partner", "101509", "B00151218"),
    ("basiima55@yahoo.co.uk", "Timothy Basiimampora", "Tirwomwe", "male", "APF/M/052", "Goldgate", "Partner/CEO", "FM1974", "CM79009104M0HL"),
    ("fmtwine@gmail.com", "Franco Brazil", "Twinomugisha", "male", "APF/M/053", "Goldgate", "Partner/ Human Resource", "FM799", "B0022375"),
    ("kasawulibaker@gmail.com", "Baker", "Kasawuli", "male", "APF/M/054", "KASAWULI ASSOCIATES", "MANAGING PARTNER", "FM1484", "CM85099101T7UL"),
    ("rkyalimpa@gmail.com", "Richard Kyalimpa", "Byaruhanga", "male", "APF/M/055", "RB Limpa Associates", "Practitioner", "FM3724", "CM80003101UGJK"),
    ("manyiredith@gmail.com", "Edith Manyire", "Komungyeya", "female", "APF/M/056", "Sakkay and Company CPA", "Managing Partner", "Fm1883", "CF70027104PQ7K"),
    ("sgabula2001@yahoo.co.uk", "Samuel Pius", "Gabula", "male", "", "SAPI & Associates", "Managing Consultant", "FM3688", "CM71008106LQPL"),
]

# Also include Twaha Kigongo (APF/M/001) and Frederick Kibbedi (APF/M/057)
# who are in the members register but have limited Google Sheet data
MEMBERS_MINIMAL = [
    ("gard662@gmail.com", "David", "Nyende", "male", "APF/M/002"),  # secondary email for Nyende
    ("", "Twaha Kigongo", "Kawaase", "male", "APF/M/001"),  # no email in sheet
    ("", "Frederick", "Kibbedi", "male", "APF/M/057"),  # no email in sheet
]


def create_members():
    created = 0
    skipped = 0
    errors = 0

    print("=" * 60)
    print("APF Member Account Creation Script")
    print("=" * 60)

    for email, first_name, last_name, gender, membership_number, org, title, icpau_reg, national_id in MEMBERS:
        if not email:
            print(f"  SKIP (no email): {first_name} {last_name}")
            skipped += 1
            continue

        email = email.strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            print(f"  EXISTS: {email} ({first_name} {last_name})")
            skipped += 1
            continue

        try:
            user = User.objects.create_user(
                email=email,
                password=DEFAULT_PASSWORD,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                role="2",  # Member
                is_active=True,
                organization=org,
                job_title=title,
                icpau_registration_number=icpau_reg,
                national_id_number=national_id,
            )
            print(f"  CREATED: {email} ({first_name} {last_name}) - {membership_number}")
            created += 1
        except Exception as e:
            print(f"  ERROR: {email} ({first_name} {last_name}) - {e}")
            errors += 1

    print()
    print("=" * 60)
    print(f"Done. Created: {created} | Skipped: {skipped} | Errors: {errors}")
    print(f"Default password for all new accounts: {DEFAULT_PASSWORD}")
    print("=" * 60)


if __name__ == "__main__":
    create_members()
