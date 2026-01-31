# train_all_models.py
import numpy as np
import pandas as pd
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier
import librosa

print("🚀 Starting Model Training...")

# Ensure directories exist
os.makedirs("core", exist_ok=True)
os.makedirs("training_data", exist_ok=True)

# ---------------------------
# Audio Data & Features
# ---------------------------
class AudioDataGenerator:
    def __init__(self, sr=22050, dur=3):
        self.sr = sr
        self.dur = dur
        self.samples = sr * dur

    def generate_silence(self, n=100):
        return [np.random.normal(0, 0.001, self.samples) for _ in range(n)], ["silence"] * n

    def generate_speech_like(self, n=150):
        data, labels = [], []
        for _ in range(n):
            t = np.linspace(0, self.dur, self.samples)
            f = np.random.uniform(85, 255)
            amp = 0.3 + 0.2 * np.sin(2*np.pi*np.random.uniform(2,8)*t)
            audio = amp*(np.sin(2*np.pi*f*t)+0.3*np.sin(2*np.pi*2.5*f*t)+0.1*np.sin(2*np.pi*3.5*f*t))
            audio += np.random.normal(0,0.05,len(audio))
            data.append(audio)
            labels.append("speech")
        return data, labels

    def generate_music_like(self, n=150):
        data, labels = [], []
        for _ in range(n):
            t = np.linspace(0, self.dur, self.samples)
            base = np.zeros(len(t))
            f0 = np.random.uniform(100,400)
            for h in [1,2,3,4,5]:
                base += (1/h) * np.sin(2*np.pi*f0*h*t)
            # simple percussion
            rhythm = np.zeros(len(t))
            beat = self.sr // 4
            for b in range(0,len(t),beat):
                rhythm[b:min(b+100,len(t))] = 0.5
            audio = 0.7*base + 0.3*rhythm + np.random.normal(0,0.02,len(t))
            data.append(audio)
            labels.append("music")
        return data, labels

    def generate_noise(self, n=100):
        data, labels = [], []
        for _ in range(n):
            audio = np.random.normal(0,0.1,self.samples)
            data.append(audio)
            labels.append("noise")
        return data, labels

class AudioFeatureExtractor:
    def extract(self, audio):
        if len(audio)==0 or np.max(np.abs(audio))<1e-6:
            return np.zeros(20)
        mfcc = librosa.feature.mfcc(y=audio,n_mfcc=13).mean(axis=1)
        mfcc_std = librosa.feature.mfcc(y=audio,n_mfcc=13).std(axis=1)[:2]
        spec_cent = np.mean(librosa.feature.spectral_centroid(y=audio))
        spec_roll = np.mean(librosa.feature.spectral_rolloff(y=audio))
        spec_bw = np.mean(librosa.feature.spectral_bandwidth(y=audio))
        zcr = np.mean(librosa.feature.zero_crossing_rate(audio))
        rms = np.sqrt(np.mean(audio**2))
        chroma = np.mean(librosa.feature.chroma_stft(y=audio),axis=1)[:2]
        return np.concatenate([mfcc, mfcc_std, [spec_cent,spec_roll,spec_bw], [zcr,rms], chroma])[:20]

def train_audio():
    print("\n🎵 Training Audio Classifier")
    gen = AudioDataGenerator()
    feat = AudioFeatureExtractor()

    silence, ls = gen.generate_silence(200)
    speech, sp = gen.generate_speech_like(300)
    music, mu = gen.generate_music_like(300)
    noise, ns = gen.generate_noise(200)

    X = [feat.extract(a) for a in silence+speech+music+noise]
    y = ls + sp + mu + ns

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled,y_enc,test_size=0.2,random_state=42,stratify=y_enc)
    clf = RandomForestClassifier(n_estimators=200,max_depth=15,min_samples_split=5,min_samples_leaf=2,class_weight='balanced',random_state=42)
    clf.fit(X_train,y_train)
    y_pred = clf.predict(X_test)
    print(f"✅ Audio Accuracy: {accuracy_score(y_test,y_pred):.4f}")
    print(classification_report(y_test,y_pred,target_names=le.classes_))

    # Save
    pickle.dump(clf,open("core/audio_classifier.pkl","wb"))
    pickle.dump(scaler,open("core/audio_scaler.pkl","wb"))
    pickle.dump(le,open("core/audio_label_encoder.pkl","wb"))

    return clf, scaler, le

# ---------------------------
# Intent Classifier
# ---------------------------
class IntentGenerator:
    def gen_scenarios(self,n_study=600,n_passive=600,n_idle=600):
        data=[]
        for _ in range(n_study):
            data.append([np.random.randint(10,50),np.random.choice(["speech","silence"],p=[0.6,0.4]),
                        np.random.randint(70,95),np.random.randint(8,30),"studying"])
        for _ in range(n_passive):
            data.append([np.random.randint(3,15),np.random.choice(["music","speech","silence"],p=[0.4,0.3,0.3]),
                        np.random.randint(30,70),np.random.randint(2,10),"passive"])
        for _ in range(n_idle):
            data.append([np.random.randint(0,5),np.random.choice(["silence","music","noise"],p=[0.5,0.3,0.2]),
                        np.random.randint(0,40),np.random.randint(0,3),"idle"])
        return pd.DataFrame(data,columns=["OCR_count","audio_label","attention","interaction","intent_label"])

def train_intent():
    print("\n🎯 Training Intent Classifier")
    gen = IntentGenerator()
    df = gen.gen_scenarios()

    audio_map = {"silence":0,"speech":1,"music":2,"noise":3}
    df['audio_val'] = df['audio_label'].map(audio_map).fillna(0)
    X = df[["OCR_count","audio_val","attention","interaction"]].values
    y = LabelEncoder().fit_transform(df['intent_label'])
    clf = XGBClassifier(n_estimators=300,max_depth=8,learning_rate=0.1,subsample=0.8,colsample_bytree=0.8,eval_metric='mlogloss',use_label_encoder=False,random_state=42)
    clf.fit(X,y)
    # Save
    pickle.dump(clf,open("core/intent_classifier.pkl","wb"))
    print("✅ Intent Classifier Saved")
    return clf

def main():
    print("\n🔧 Training All Models")
    train_audio()
    train_intent()
    print("\n🎉 All models trained successfully!")

if __name__=="__main__":
    main()
