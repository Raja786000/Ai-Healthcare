from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
import sqlite3, json, os, re, subprocess, urllib.parse
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DB = ROOT / 'healthbridge.db'
KB = ROOT / 'data' / 'knowledge.json'

app = FastAPI(title='HealthBridge AI', version='4.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

LANG_NAMES = {'en':'English','hi':'Hindi','pa':'Punjabi','bn':'Bengali','ta':'Tamil','te':'Telugu','mr':'Marathi','gu':'Gujarati'}

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: str = 'en'
    session_id: str = 'demo'
    context: Optional[dict] = None

class PlanRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=100)
    language: str = 'en'
    age_group: str = 'adult'
    preferences: List[str] = []

class TriageRequest(BaseModel):
    symptoms: str = Field(min_length=1, max_length=2000)
    duration: str = 'today'
    severity: int = Field(default=3, ge=1, le=5)
    age_group: str = 'adult'
    pregnancy: bool = False
    red_flags: List[str] = []
    language: str = 'en'

class ResourceRequest(BaseModel):
    city: str = ''
    state: str = ''
    service: str = 'general healthcare'

class AssessmentRequest(BaseModel):
    # Step 1 – Symptom intake
    symptoms: str = Field(min_length=1, max_length=2000)
    body_system: str = 'general'          # respiratory, cardiac, digestive, neurological, musculoskeletal, skin, mental, general
    # Step 2 – Context
    duration: str = 'today'               # today, 1-2 days, 3-7 days, more than 1 week
    severity: int = Field(default=3, ge=1, le=5)
    age_group: str = 'adult'             # child, adult, older adult, pregnant
    # Step 3 – Red flags
    red_flags: List[str] = []
    # Step 4 – Navigation preferences
    language: str = 'en'
    city: str = ''
    state: str = ''
    session_id: str = 'demo'

# ---------------- Data ----------------
EMERGENCY = [
    r'cannot breathe', r"can't breathe", r'severe breathing', r'breathing difficulty', r'not breathing',
    r'unconscious', r'not responding', r'severe chest pain', r'heavy bleeding', r'stroke', r'face drooping',
    r'slurred speech', r'seizure', r'convulsion', r'suicide', r'self[- ]?harm', r'poisoning', r'overdose',
    r'सांस लेने में बहुत दिक्कत', r'सांस नहीं', r'बेहोश', r'सीने में तेज दर्द', r'बहुत ज्यादा खून', r'आत्महत्या', r'दौरा', r'जहर',
    r'ਸਾਹ ਲੈਣ ਵਿੱਚ ਬਹੁਤ ਦਿੱਕਤ', r'ਬੇਹੋਸ਼', r'ਛਾਤੀ ਵਿੱਚ ਤੇਜ਼ ਦਰਦ', r'ਬਹੁਤ ਖੂਨ', r'ਆਤਮਹੱਤਿਆ', r'ਦੌਰਾ',
    r'শ্বাস নিতে পারছি না', r'অজ্ঞান', r'আত্মহত্যা', r'শ্বাসকষ্ট',
    r'மூச்சு விட முடியவில்லை', r'மயக்கம்', r'தற்கொலை',
    r'శ్వాస తీసుకోలేకపోతున్నాను', r'స్పృహ కోల్పోయాను',
    r'श्वास घेता येत नाही', r'बेशुद्ध', r'आत्महत्या',
    r'શ્વાસ લઈ શકતો નથી', r'બેભાન', r'આત્મહત્યા'
]
HIGH = [
    r'blood in (vomit|stool|urine)', r'vomit.*blood', r'persistent vomiting', r'severe dehydration', r'confusion',
    r'fainting', r'pregnant.*bleed', r'pregnan.*pain', r'high fever.*child', r'fever.*3 days', r'rapidly worsening',
    r'खून.*उल्टी', r'खून.*मल', r'बेहोशी', r'लगातार उल्टी', r'गर्भ.*खून', r'बच्च.*तेज बुखार', r'तीन दिन.*बुखार',
    r'ਖੂਨ.*ਉਲਟੀ', r'ਲਗਾਤਾਰ ਉਲਟੀ', r'ਗਰਭ.*ਖੂਨ',
    r'রক্ত.*বমি', r'ক্রমাগত বমি', r'গর্ভ.*রক্ত',
    r'இரத்தம்.*வாந்தி', r'தொடர்ந்த வாந்தி',
    r'రక్తం.*వాంతి', r'నిరంతర వాంతి'
]
MED_DOSING = [r'how much .*mg', r'dose', r'dosage', r'how many tablets', r'खुराक', r'कितनी गोली', r'ਦਵਾਈ ਦੀ ਖੁਰਾਕ']
INTENT_PATTERNS = {
    'vaccination':['vaccine','vaccination','immunization','टीका','टीकाकरण','ਟੀਕਾ','টিকা'],
    'maternal_child':['pregnan','pregnancy','mother','maternal','baby','child','infant','गर्भ','मां','बच्च','ਬੱਚ','ਗਰਭ'],
    'prevention':['prevent','healthy','nutrition','diet','exercise','sleep','hygiene','smoking','tobacco','स्वस्थ','पोषण','व्यायाम','नींद','ਧੂਮਪਾਨ'],
    'symptom':['symptom','pain','fever','cough','headache','dizzy','diarr','vomit','rash','breath','दर्द','बुखार','खांसी','सिरदर्द','चक्कर','उल्टी','ਦਰਦ','ਬੁਖਾਰ'],
    'mental_wellbeing':['stress','anxiety','sad','mental','panic','lonely','तनाव','चिंता','उदास','मानसिक','ਤਣਾਅ','ਚਿੰਤਾ'],
    'access':['doctor','hospital','clinic','telemedicine','appointment','resource','near me','care','डॉक्टर','अस्पताल','क्लिनिक','सेवा','ਡਾਕਟਰ','ਹਸਪਤਾਲ'],
    'medicine_safety':['medicine','medication','tablet','dose','drug','दवा','गोली','खुराक','ਦਵਾਈ','ਗੋਲੀ'],
    'myth_check':['myth','true or false','is it true','गलतफहमी','सच है','ਮਿੱਥ','ਸੱਚ ਹੈ']
}

BODY_SYSTEM_TIPS = {
    'respiratory':['Avoid smoke, dust and strong fumes.','If you have a cough lasting more than 3 weeks, get a professional evaluation for TB.','Wash hands to reduce spread of respiratory infections.'],
    'cardiac':['Limit salt, processed foods and tobacco.','Regular moderate activity supports heart health — check with a professional if you have existing conditions.','Know the warning signs: chest pain, arm or jaw pain, sudden breathlessness — call 112 immediately.'],
    'digestive':['Use safe drinking water and practice hand hygiene.','Oral rehydration solution (ORS) helps manage mild to moderate dehydration from diarrhoea.','Seek care if vomiting or diarrhoea lasts more than 2 days or includes blood.'],
    'neurological':['Track headache frequency and triggers.','Sudden severe headache, vision changes, weakness, or confusion are emergency signs — call 112.','Sleep, hydration and stress management support brain health.'],
    'musculoskeletal':['Rest injured areas and avoid further strain.','Cold packs in the first 48 hours and gentle movement after can help minor injuries.','Persistent or worsening joint pain deserves professional evaluation.'],
    'skin':['Keep skin clean and dry; avoid sharing towels or clothing to prevent spread.','New or changing skin lesions that do not heal should be assessed professionally.','Severe rashes with breathing difficulty or swelling are emergency signs.'],
    'mental':['Speak to someone you trust about what you are experiencing.','Breathing exercises and a structured daily routine can reduce distress.','If feelings of hopelessness are persistent or self-harm thoughts occur, seek professional help immediately.'],
    'general':['Track symptoms — what they are, when they started and what makes them better or worse.','Stay hydrated and rest if acutely unwell.','See a qualified professional if symptoms are severe, worsening or new.']
}

TOPICS = [
 {'id':'assessment','title':'Health assessment','icon':'📋','desc':'4-step guided intake — symptoms to care plan.','prompt':'__assessment__'},
 {'id':'triage','title':'Check symptoms safely','icon':'🩺','desc':'A guided urgency check — not a diagnosis.','prompt':'Help me check how urgent my symptoms might be.'},
 {'id':'vaccination','title':'Vaccination guide','icon':'💉','desc':'Understand records, schedules and questions to ask.','prompt':'Help me understand vaccination and how to check what I may need.'},
 {'id':'prevention','title':'Prevention coach','icon':'🌱','desc':'Build a practical prevention routine.','prompt':'Give me a simple prevention plan for staying healthy.'},
 {'id':'maternal_child','title':'Mother & child','icon':'🤱','desc':'Pregnancy and child-health awareness.','prompt':'What preventive care is important during pregnancy and early childhood?'},
 {'id':'mental_wellbeing','title':'Mental wellbeing','icon':'🧠','desc':'Simple, supportive wellbeing guidance.','prompt':'Give me simple ways to support mental wellbeing.'},
 {'id':'medicine_safety','title':'Medicine safety','icon':'💊','desc':'Safer questions to ask before taking medicines.','prompt':'What should I check before taking a medicine?'}
]

PLANS = {
 'daily wellness':['Build a regular sleep routine (7–9 hours for adults).','Choose a varied diet with vegetables, fruits, whole grains/fibre and suitable protein sources.','Choose physical activity that fits your age and ability, starting gradually if needed.','Practice hand hygiene and safer food/water habits.','Keep appropriate preventive check-ups and vaccinations up to date.','Limit tobacco, alcohol and highly processed foods.'],
 'vaccination':['Gather your vaccination record if available.','Ask a qualified health professional which vaccines fit your age, pregnancy status, health conditions, work and travel.','Use an official vaccination service or government facility for guidance.','Record doses and the next recommended date.','Do not use social-media forwards as your vaccination schedule.'],
 'maternal & child':['Start antenatal care early and keep scheduled visits.','Ask a qualified professional about nutrition, supplements and screening.','Keep the child\'s immunization record current.','Use routine growth/development checks and ask about concerns early.','Seek urgent help for heavy bleeding, severe pain, fainting, severe breathing difficulty, seizures or unconsciousness.'],
 'mental wellbeing':['Protect regular sleep and daily routines.','Stay connected with trusted people.','Try simple stress-management practices such as breathing, movement or quiet time.','If distress persists or disrupts daily life, seek professional support.','If there is immediate self-harm risk, seek emergency help now.'],
 'respiratory health':['Avoid tobacco smoke, indoor air pollution and burning biomass fuels where possible.','Complete any prescribed TB or respiratory treatment course fully.','Seek evaluation for cough lasting more than 3 weeks, blood in sputum, or unexplained weight loss.','Use masks appropriately during respiratory illness outbreaks.'],
 'diabetes prevention':['Maintain a healthy weight through balanced diet and regular physical activity.','Limit added sugars and refined carbohydrates.','Get periodic blood-sugar checks if you have risk factors (family history, overweight, over 40).','Quit tobacco — it increases cardiovascular and metabolic risk.'],
 'heart health':['Reduce salt intake and avoid processed/fried foods.','Stay physically active — at least 150 minutes of moderate activity per week.','Manage stress through routine, sleep and social connection.','Know your blood pressure; if elevated, seek professional guidance.','Quit smoking and limit alcohol.']
}

# Multilingual emergency messages
EMERGENCY_MSG = {
    'en':'⚠️ **Get urgent help now.** This may be an emergency. In India, call **112** or go to the nearest emergency department. Do not wait for an AI response.',
    'hi':'⚠️ **अभी मदद लें।** यह संभावित आपात स्थिति हो सकती है। भारत में **112** पर कॉल करें या नजदीकी आपातकालीन विभाग जाएँ। AI उत्तर का इंतज़ार न करें।',
    'pa':'⚠️ **ਤੁਰੰਤ ਮਦਦ ਲਓ।** ਇਹ ਸੰਭਾਵਿਤ ਐਮਰਜੈਂਸੀ ਹੋ ਸਕਦੀ ਹੈ। ਭਾਰਤ ਵਿੱਚ **112** ਤੇ ਕਾਲ ਕਰੋ ਜਾਂ ਨੇੜਲੇ ਐਮਰਜੈਂਸੀ ਵਿਭਾਗ ਵਿੱਚ ਜਾਓ।',
    'bn':'⚠️ **এখনই সাহায্য নিন।** এটি একটি জরুরি অবস্থা হতে পারে। ভারতে **112** নম্বরে কল করুন বা নিকটতম জরুরি বিভাগে যান।',
    'ta':'⚠️ **இப்போதே உதவி பெறுங்கள்।** இது அவசரநிலை ஆக இருக்கலாம். இந்தியாவில் **112** அழைக்கவும் அல்லது அருகிலுள்ள அவசர பிரிவிற்கு செல்லவும்।',
    'te':'⚠️ **ఇప్పుడే సహాయం పొందండి।** ఇది అత్యవసర పరిస్థితి కావచ్చు. భారతదేశంలో **112** కి కాల్ చేయండి లేదా సమీప అత్యవసర విభాగానికి వెళ్ళండి।',
    'mr':'⚠️ **आत्ताच मदत घ्या।** ही आणीबाणीची परिस्थिती असू शकते. भारतात **112** वर कॉल करा किंवा जवळच्या आपत्कालीन विभागात जा।',
    'gu':'⚠️ **હમણાં જ મદદ મેળવો।** આ કટોકટી હોઈ શકે છે. ભારતમાં **112** પર કૉલ કરો અથવा નજીકના ઈમર્જન્સી વિભાગ પર જાઓ।'
}

# Multilingual "general intro" messages
INTRO_MSG = {
    'hi':'मैं स्वास्थ्य विषय को आसान भाषा में समझा सकता हूँ, रोकथाम की योजना बना सकता हूँ और भरोसेमंद सेवाओं तक पहुँचने में मदद कर सकता हूँ। **📋 स्वास्थ्य मूल्यांकन** शुरू करने के लिए ऊपर का बटन दबाएं, या अपना सवाल लिखें।',
    'pa':'ਮੈਂ ਸਿਹਤ ਵਿਸ਼ੇ ਨੂੰ ਸੌਖੀ ਭਾਸ਼ਾ ਵਿੱਚ ਸਮਝਾ ਸਕਦਾ ਹਾਂ, ਬਚਾਅ ਦੀ ਯੋਜਨਾ ਬਣਾ ਸਕਦਾ ਹਾਂ ਅਤੇ ਭਰੋਸੇਯੋਗ ਸੇਵਾਵਾਂ ਤੱਕ ਪਹੁੰਚ ਵਿੱਚ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ। **📋 ਸਿਹਤ ਮੁਲਾਂਕਣ** ਸ਼ੁਰੂ ਕਰਨ ਲਈ ਉੱਪਰ ਦਾ ਬਟਨ ਦਬਾਓ।',
    'bn':'আমি সহজ ভাষায় স্বাস্থ্য বিষয়ক তথ্য দিতে পারি, প্রতিরোধমূলক পরিকল্পনা তৈরি করতে পারি এবং বিশ্বস্ত সেবায় পথ দেখাতে পারি। **📋 স্বাস্থ্য মূল্যায়ন** শুরু করতে উপরের বাটন চাপুন।',
    'ta':'நான் எளிய மொழியில் சுகாதார தகவல்களை விளக்க முடியும், தடுப்பு திட்டங்களை உருவாக்க முடியும் மற்றும் நம்பகமான சேவைகளை அணுக உதவ முடியும். **📋 சுகாதார மதிப்பீடு** தொடங்க மேலே உள்ள பொத்தானை அழுத்தவும்।',
    'te':'నేను సులభమైన భాషలో ఆరోగ్య సమాచారం వివరించగలను, నివారణ ప్రణాళికలు రూపొందించగలను మరియు నమ్మకమైన సేవలకు దారి చూపగలను। **📋 ఆరోగ్య అంచనా** ప్రారంభించడానికి పైన ఉన్న బటన్ నొక్కండి।',
    'mr':'मी सोप्या भाषेत आरोग्य माहिती सांगू शकतो, प्रतिबंधात्मक योजना बनवू शकतो आणि विश्वासार्ह सेवांपर्यंत पोहोचण्यास मदत करू शकतो। **📋 आरोग्य मूल्यांकन** सुरू करण्यासाठी वरील बटण दाबा।',
    'gu':'હું સરળ ભાષામાં સ્વાસ્થ્ય માહિતી સમજાવી શકું છું, નિવારક યોજના બનાવી શકું છું અને વિશ્વસનીય સેવાઓ સુધી પહોંચવામાં મદદ કરી શકું છું। **📋 સ્વાસ્થ્ય મૂલ્યાંકન** શરૂ કરવા ઉપર આપેલ બટન દબાવો।'
}

# ---------------- Persistence ----------------
def init_db():
    con=sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,session_id TEXT,role TEXT,content TEXT,language TEXT,created_at TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,session_id TEXT,event TEXT,metadata TEXT,created_at TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS assessments(id INTEGER PRIMARY KEY,session_id TEXT,urgency TEXT,intent TEXT,body_system TEXT,summary TEXT,created_at TEXT)')
    con.commit(); con.close()
init_db()

def load_kb(): return json.loads(KB.read_text(encoding='utf-8'))
def now(): return datetime.now(timezone.utc).isoformat()
def save_message(session,role,content,language):
    con=sqlite3.connect(DB); con.execute('INSERT INTO messages(session_id,role,content,language,created_at) VALUES(?,?,?,?,?)',(session,role,content,language,now())); con.commit(); con.close()
def log_event(session,event,metadata):
    con=sqlite3.connect(DB); con.execute('INSERT INTO events(session_id,event,metadata,created_at) VALUES(?,?,?,?)',(session,event,json.dumps(metadata,ensure_ascii=False),now())); con.commit(); con.close()
def save_assessment(session,urgency,intent,body_system,summary):
    con=sqlite3.connect(DB); con.execute('INSERT INTO assessments(session_id,urgency,intent,body_system,summary,created_at) VALUES(?,?,?,?,?,?)',(session,urgency,intent,body_system,summary,now())); con.commit(); con.close()

def tokenize(s): return set(re.findall(r'[a-zA-Z]{3,}|[\u0900-\u0dff]{2,}|[\u0a00-\u0a7f]{2,}|[\u0980-\u09ff]{2,}|[\u0b80-\u0bff]{2,}|[\u0c00-\u0c7f]{2,}|[\u0b00-\u0b7f]{2,}|[\u0a80-\u0aff]{2,}', s.lower()))
def retrieve(message,limit=6):
    terms=tokenize(message); scored=[]
    for item in load_kb():
        text=(item['title']+' '+item['content']+' '+' '.join(item.get('keywords',[]))).lower()
        score=sum(1 for t in terms if t in text)
        if score: scored.append((score,item))
    return [x[1] for x in sorted(scored,key=lambda x:x[0],reverse=True)[:limit]]

def classify(message):
    m=message.lower(); risk='routine'
    if any(re.search(p,m) for p in EMERGENCY): risk='emergency'
    elif any(re.search(p,m) for p in HIGH): risk='high'
    intent='general'; best=0
    for name,words in INTENT_PATTERNS.items():
        score=sum(1 for w in words if w in m)
        if score>best: best,intent=score,name
    return intent,risk

# ---------------- Agents ----------------
def safety_agent(message,risk,language):
    if risk=='emergency': return {'level':'EMERGENCY','instruction':'Seek emergency help now. In India call 112 or go to the nearest emergency department. Do not wait for an AI response.'}
    if risk=='high': return {'level':'HIGH','instruction':'This may need prompt professional assessment. Contact a qualified healthcare professional or appropriate local service soon.'}
    return {'level':'ROUTINE','instruction':'General health information only. If symptoms are severe, worsening, unusual or persistent, seek professional care.'}

def redflag_triage(req):
    text=req.symptoms.lower(); risk='routine'; reasons=[]
    if any(re.search(p,text) for p in EMERGENCY) or req.red_flags:
        risk='emergency'; reasons.append('A potential emergency warning sign was reported.')
    elif any(re.search(p,text) for p in HIGH) or req.severity>=5 or (req.duration in ['3-7 days','more than 1 week'] and req.severity>=4):
        risk='high'; reasons.append('The combination of symptoms, severity or duration may need prompt professional assessment.')
    elif req.severity>=4 or req.duration in ['3-7 days','more than 1 week']:
        risk='moderate'; reasons.append('Symptoms that are stronger or persistent deserve professional assessment if they do not improve.')
    else: reasons.append('No emergency signal was detected from the information provided.')
    action={'emergency':'Call 112 or go to the nearest emergency department now.','high':'Arrange prompt assessment by a qualified healthcare professional.','moderate':'Consider a healthcare consultation, especially if symptoms persist or worsen.','routine':'Monitor how you feel, use general self-care, and seek care if symptoms worsen or new warning signs appear.'}[risk]
    return {'urgency':risk,'reasons':reasons,'action':action,'disclaimer':'This is a safety-oriented triage aid, not a diagnosis.'}

def resource_agent(service='general healthcare',city='',state=''):
    resources=[
      {'name':'Emergency 112','type':'Emergency','description':'Pan-India emergency response system.','url':'https://112.gov.in/','action':'Call 112'},
      {'name':'e-Sanjeevani','type':'Telemedicine','description':'Government telemedicine pathway for remote consultations.','url':'https://esanjeevani.mohfw.gov.in/','action':'Open service'},
      {'name':'Ministry of Health & Family Welfare','type':'Government','description':'Official national health programmes and public-health information.','url':'https://mohfw.gov.in/','action':'Visit official site'},
      {'name':'National Health Authority','type':'Government','description':'India digital-health programmes and citizen services.','url':'https://www.nha.gov.in/','action':'Visit official site'},
      {'name':'WHO Health Literacy','type':'Trusted information','description':'Evidence-informed health literacy resources.','url':'https://www.who.int/news-room/fact-sheets/detail/health-literacy','action':'Read guidance'}]
    if city:
        q=urllib.parse.quote_plus(f'{service} near {city} {state}'.strip())
        resources.insert(0,{'name':f'Find {service} near {city}','type':'Local pathway','description':'Open a map search. Verify hours, availability and facility details before travelling.','url':f'https://www.google.com/maps/search/?api=1&query={q}','action':'Open map'})
    return resources

def prevention_agent(goal,language,age_group='adult',preferences=None):
    items=list(PLANS.get(goal.lower(),PLANS['daily wellness']))
    if age_group=='older adult': items.insert(1,'Ask a qualified professional about age-appropriate screening, medication review and fall prevention.')
    if age_group=='child': items.insert(1,'Use age-appropriate nutrition, activity, sleep and routine growth/development checks.')
    if age_group=='pregnant': items.insert(0,'Keep scheduled antenatal visits and discuss any warning signs promptly with a qualified professional.')
    return {'goal':goal,'age_group':age_group,'steps':items,'note':'A general prevention checklist — not personalized medical advice.'}

def assessment_agent(req: AssessmentRequest):
    """Full patient-friendly assessment: intake → red-flag check → prevention → resources."""
    # Step 1 — Triage
    triage_req = TriageRequest(symptoms=req.symptoms,duration=req.duration,severity=req.severity,age_group=req.age_group,pregnancy=(req.age_group=='pregnant'),red_flags=req.red_flags,language=req.language)
    triage_result = redflag_triage(triage_req)
    urgency = triage_result['urgency']

    # Step 2 — Intent classification from symptoms
    intent, risk = classify(req.symptoms)

    # Step 3 — Prevention plan based on body system + triage risk
    goal_map = {
        'respiratory':'respiratory health','cardiac':'heart health','mental':'mental wellbeing',
        'maternal_child':'maternal & child','vaccination':'vaccination','digestive':'daily wellness',
        'diabetes':'diabetes prevention'
    }
    plan_goal = goal_map.get(req.body_system, goal_map.get(intent,'daily wellness'))
    prevention = prevention_agent(plan_goal, req.language, req.age_group)

    # Step 4 — Body-system specific tips
    tips = BODY_SYSTEM_TIPS.get(req.body_system, BODY_SYSTEM_TIPS['general'])

    # Step 5 — Resources
    resources = resource_agent(
        service='emergency department' if urgency=='emergency' else
                ('general healthcare' if not req.city else 'general healthcare'),
        city=req.city, state=req.state
    )

    # Step 6 — Knowledge refs
    refs = retrieve(req.symptoms)

    # Step 7 — Summary text
    lang = req.language
    if urgency=='emergency':
        summary = EMERGENCY_MSG.get(lang, EMERGENCY_MSG['en'])
    else:
        urgency_label = {'high':'HIGH PRIORITY','moderate':'MODERATE CONCERN','routine':'ROUTINE'}[urgency]
        summary = (
            f'### Assessment complete — {urgency_label}\n\n'
            f'**What you described:** {req.symptoms}\n\n'
            f'**Urgency level:** {urgency.upper()} — {triage_result["action"]}\n\n'
            f'**Body system focus:** {req.body_system.title()}\n\n'
            f'**Key self-care steps:**\n' + '\n'.join(f'- {t}' for t in tips[:3]) + '\n\n'
            f'**Prevention checklist:** See the {prevention["goal"]} plan below.\n\n'
            f'_This is health-awareness guidance, not a diagnosis. A qualified professional should assess your situation._'
        )

    return {
        'urgency': urgency,
        'triage': triage_result,
        'intent': intent,
        'body_system': req.body_system,
        'summary': summary,
        'tips': tips,
        'prevention': prevention,
        'resources': resources,
        'sources': [{'title':r['title'],'url':r['url'],'category':r.get('category','')} for r in refs],
        'disclaimer': 'HealthBridge provides health awareness information only. It does not diagnose, prescribe, or replace a qualified healthcare professional.',
        'emergency_number': '112',
        'language': lang
    }

# ---------------- AI provider ----------------
SYSTEM_PROMPT='''You are HealthBridge AI, a public-health awareness and care-navigation assistant for underserved communities in India. You are not a doctor. Do not diagnose, prescribe, recommend medication doses, or create false certainty. Explain health information in simple language, support prevention, help users recognize when professional care may be needed, and guide them to trusted services. Use only supplied reference notes for factual health claims. If emergency risk is flagged, give urgent-care instructions first and do not speculate about diagnosis. Structure responses with short headings using ###: ### Simple explanation, ### What you can do, ### When to seek care, ### Sources. Use bullet points (- ) for lists. Requested language: {language}.'''

def bob_answer(prompt):
    cmd=['bob','run',prompt]; env=os.environ.copy()
    if env.get('BOB_TEAM_ID'): cmd += ['--team-id',env['BOB_TEAM_ID']]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=90,env=env,shell=False)
    if result.returncode!=0: raise RuntimeError(result.stderr.strip() or 'Bob returned an error')
    return result.stdout.strip()

async def watsonx_answer(prompt):
    url=os.getenv('WATSONX_URL'); key=os.getenv('WATSONX_API_KEY'); project=os.getenv('WATSONX_PROJECT_ID'); model=os.getenv('WATSONX_MODEL_ID','ibm/granite-3-3-8b-instruct')
    if not all([url,key,project]): raise RuntimeError('watsonx credentials incomplete')
    async with httpx.AsyncClient(timeout=60) as client:
        token=(await client.post('https://iam.cloud.ibm.com/identity/token',data={'grant_type':'urn:ibm:params:oauth:grant-type:apikey','apikey':key},headers={'Content-Type':'application/x-www-form-urlencoded'})).json()['access_token']
        r=await client.post(url.rstrip('/')+'/ml/v1/text/chat?version=2025-10-25',headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},json={'model_id':model,'project_id':project,'messages':[{'role':'user','content':prompt}],'max_tokens':850})
        r.raise_for_status(); return r.json()['choices'][0]['message']['content']

def demo_compose(message,language,intent,risk,refs,safety):
    if risk=='emergency': return EMERGENCY_MSG.get(language, EMERGENCY_MSG['en'])
    if intent=='medicine_safety' and any(re.search(p,message.lower()) for p in MED_DOSING):
        return '### Medication safety\nI can explain general medicine-safety principles, but I should not choose a dose for you.\n\n**What to check:**\n- Read the medicine label or prescription carefully\n- Check for known allergies\n- Consider other medicines you are taking\n- Check age and pregnancy considerations\n- Ask a pharmacist or qualified clinician if unsure\n\n**When to seek care:** seek urgent help for severe allergic reactions, trouble breathing, unconsciousness, or suspected overdose.'
    if intent=='vaccination':
        r=next((x for x in refs if 'vaccin' in x['title'].lower() or 'immuniz' in x['title'].lower()),refs[0] if refs else None)
        base=f'### {r["title"]}\n{r["content"]}\n\n' if r else ''
        return base+'**What you can do:**\n- Gather your vaccination record if available\n- Ask a qualified health professional about schedules for your age and circumstances\n- Use a government vaccination facility or official service\n- Record each dose and the next due date\n\n**Next step:** '+safety['instruction']
    if intent=='prevention':
        r=next((x for x in refs if 'prevent' in x['title'].lower() or 'health' in x['title'].lower()),refs[0] if refs else None)
        base=f'### {r["title"]}\n{r["content"]}\n\n' if r else '### Staying healthy\n'
        return base+'**Key prevention habits:**\n- Regular sleep (7–9 hours)\n- Varied diet with vegetables, fruits and whole grains\n- Physical activity suited to your ability\n- Hand hygiene and safe food/water habits\n- Keep vaccinations and check-ups up to date\n\n**Next step:** '+safety['instruction']
    if intent=='mental_wellbeing':
        return '### Mental wellbeing\nMental health is part of overall health. It\'s normal to feel stress, anxiety or sadness — support is available.\n\n**What you can do:**\n- Protect regular sleep and daily routines\n- Stay connected with trusted people\n- Try breathing exercises or gentle movement\n- Reduce known stressors where possible\n\n**When to seek care:** if distress persists, disrupts daily life, or self-harm thoughts arise, please speak to a health professional.\n\n**Next step:** '+safety['instruction']
    if intent=='maternal_child':
        r=next((x for x in refs if 'pregnan' in x['title'].lower() or 'child' in x['title'].lower() or 'maternal' in x['title'].lower()),refs[0] if refs else None)
        base=f'### {r["title"]}\n{r["content"]}\n\n' if r else '### Maternal and child health\n'
        return base+'**Key steps:**\n- Start antenatal care early and keep all scheduled visits\n- Keep the child\'s immunization record current\n- Seek urgent help for heavy bleeding, severe pain, fainting, or seizures\n\n**Next step:** '+safety['instruction']
    if intent=='symptom':
        if refs:
            r=refs[0]
            return f'### {r["title"]}\n{r["content"]}\n\n**What you can do:**\n- Track your symptoms — when they started, what makes them better or worse\n- Stay hydrated and rest if acutely unwell\n- Use the **Symptom Check** tool above for a guided safety check\n\n**Next step:** {safety["instruction"]}'
        return '### Symptom guidance\nUse the **Symptom Check** tool on this page for a guided safety check. It will assess urgency and suggest your next step.\n\n**When to seek care immediately:** severe breathing difficulty, chest pain, unconsciousness, seizure, heavy bleeding, or stroke signs — call **112**.\n\n**Next step:** '+safety['instruction']
    if intent=='access':
        return '### Care navigation\nTell me your **city + state** and whether you need a general clinic, government hospital, maternal/child care, emergency care, or telemedicine.\n\n**Official pathways:**\n- **e-Sanjeevani** — free government telemedicine (esanjeevani.mohfw.gov.in)\n- **MOHFW** — national health programme information (mohfw.gov.in)\n- **Emergency** — call **112** for any life-threatening situation\n\n**Next step:** '+safety['instruction']
    if intent=='myth_check': return '### Health information check\nI can help compare a health claim against trusted public-health information. Paste the claim and I will separate what is supported, uncertain, or unsafe to assume.\n\n**Good practice:**\n- Check claims against WHO or MOHFW sources\n- Be cautious of social-media health forwards\n- Ask a qualified professional about anything that affects your care'
    if refs:
        r=refs[0]
        return f'### {r["title"]}\n{r["content"]}\n\n**Next step:** {safety["instruction"]}'
    return INTRO_MSG.get(language,'### HealthBridge\nI can explain a health topic simply, help you check urgency, build a prevention plan, and connect you with trusted care pathways.\n\n**Try:**\n- 📋 Start a **Health Assessment** for guided symptom-to-care support\n- Ask about prevention, vaccination, pregnancy, mental wellbeing, or medicines\n- Use the **Symptom Check** tool for a 30-second urgency check\n\n**Next step:** '+safety['instruction'])

async def ai_compose(message,language,intent,risk,refs,safety,context=None):
    provider=os.getenv('AI_PROVIDER','demo').lower()
    context_notes='\n'.join(f'- {r["title"]}: {r["content"]} [source: {r["url"]}]' for r in refs)
    prompt=SYSTEM_PROMPT.format(language=LANG_NAMES.get(language,'English'))+f'\nIntent: {intent}\nUrgency: {safety["level"]} — {safety["instruction"]}\nReference notes:\n{context_notes}\nConversation context: {json.dumps(context or {},ensure_ascii=False)}\nUser message: {message}'
    if provider=='bob': return bob_answer(prompt),'ibm-bob'
    if provider=='watsonx': return await watsonx_answer(prompt),'ibm-watsonx'
    return demo_compose(message,language,intent,risk,refs,safety),'demo'

# ---------------- API ----------------
@app.get('/')
def home(): return FileResponse(ROOT/'frontend'/'index.html')
@app.get('/app.js')
def js(): return FileResponse(ROOT/'frontend'/'app.js',media_type='application/javascript')
@app.get('/styles.css')
def css(): return FileResponse(ROOT/'frontend'/'styles.css',media_type='text/css')
@app.get('/sw.js')
def sw(): return FileResponse(ROOT/'frontend'/'sw.js',media_type='application/javascript')
@app.get('/manifest.webmanifest')
def manifest(): return FileResponse(ROOT/'frontend'/'manifest.webmanifest',media_type='application/manifest+json')

@app.get('/api/health')
def health():
    provider=os.getenv('AI_PROVIDER','demo').lower()
    return {'status':'ok','provider':provider,'bob_configured':bool(os.getenv('BOB_API_KEY') or provider=='bob'),'languages':LANG_NAMES,'agents':['Intent Router','Safety Guard','Evidence Retriever','Triage Agent','Assessment Agent','Prevention Coach','Care Navigator','Language Agent','Response Composer']}

@app.get('/api/topics')
def topics(): return TOPICS

@app.post('/api/triage')
def triage(req:TriageRequest):
    result=redflag_triage(req); log_event('triage','triage_completed',result); return result

@app.post('/api/assessment')
def assessment(req:AssessmentRequest):
    result=assessment_agent(req)
    log_event(req.session_id,'assessment_completed',{'urgency':result['urgency'],'intent':result['intent'],'body_system':result['body_system']})
    save_assessment(req.session_id,result['urgency'],result['intent'],result['body_system'],result['summary'][:500])
    return result

@app.post('/api/prevention-plan')
def prevention_plan(req:PlanRequest): return prevention_agent(req.goal,req.language,req.age_group,req.preferences)

@app.get('/api/resources')
def resources(city:str='',state:str='',service:str='general healthcare'): return resource_agent(service,city,state)

@app.get('/api/knowledge')
def knowledge():
    return [{'title':x['title'],'summary':x['content'],'url':x['url'],'category':x.get('category','General'),'keywords':x.get('keywords',[]) } for x in load_kb()]

@app.get('/api/history/{session_id}')
def history(session_id:str):
    con=sqlite3.connect(DB); rows=con.execute('SELECT role,content,language,created_at FROM messages WHERE session_id=? ORDER BY id',(session_id,)).fetchall(); con.close()
    return [{'role':a,'content':b,'language':c,'created_at':d} for a,b,c,d in rows]

@app.get('/api/assessments/{session_id}')
def get_assessments(session_id:str):
    con=sqlite3.connect(DB); rows=con.execute('SELECT urgency,intent,body_system,summary,created_at FROM assessments WHERE session_id=? ORDER BY id DESC LIMIT 10',(session_id,)).fetchall(); con.close()
    return [{'urgency':a,'intent':b,'body_system':c,'summary':d,'created_at':e} for a,b,c,d,e in rows]

@app.post('/api/chat')
async def chat(req:ChatRequest):
    intent,risk=classify(req.message); safety=safety_agent(req.message,risk,req.language); refs=retrieve(req.message)
    save_message(req.session_id,'user',req.message,req.language)
    log_event(req.session_id,'agent_pipeline',{'intent':intent,'risk':risk,'retrieved':len(refs)})
    try: answer,provider=await ai_compose(req.message,req.language,intent,risk,refs,safety,req.context)
    except Exception:
        answer=demo_compose(req.message,req.language,intent,risk,refs,safety)+'\n\n_AI provider unavailable; HealthBridge safe local mode is active._'; provider='safe-fallback'
    save_message(req.session_id,'assistant',answer,req.language)
    trace=[
      {'agent':'Intent Router','result':intent,'detail':'Classified the user goal'},
      {'agent':'Safety Guard','result':risk,'detail':'Checked emergency and high-risk language'},
      {'agent':'Evidence Retriever','result':f'{len(refs)} notes','detail':'Matched curated public-health references'},
      {'agent':'Triage Agent','result':'active','detail':'Safety-first escalation rules applied'},
      {'agent':'Assessment Agent','result':'ready','detail':'Full guided assessment available via 📋 button'},
      {'agent':'Language Agent','result':LANG_NAMES.get(req.language,'English'),'detail':'Prepared the response language'},
      {'agent':'Response Composer','result':provider,'detail':'Generated the final answer'}]
    return {'answer':answer,'intent':intent,'urgency':risk,'provider':provider,'safety':safety,'sources':[{'title':r['title'],'url':r['url']} for r in refs],'agent_trace':trace}

if __name__=='__main__':
    import uvicorn
    uvicorn.run('main:app',host='0.0.0.0',port=int(os.getenv('PORT','8000')),reload=False)
