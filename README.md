# 🛫 AI Travel Agent (TravelAI)

Yapay zeka destekli akıllı seyahat asistanı. LangGraph ve LangChain kullanarak geliştirilmiş, gerçek zamanlı hava durumu, otel ve uçuş bilgisi sunan chatbot uygulaması.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange.svg)

## ✨ Özellikler

- 🌤️ **Hava Durumu Sorgulama** - Dünya genelinde anlık hava durumu bilgisi
- 🏨 **Otel Arama** - Bütçe ve yıldız sayısına göre otel önerileri
- ✈️ **Uçuş Arama** - Havalimanları arası uçuş seçenekleri ve fiyatları
- 💬 **Doğal Dil İşleme** - Türkçe konuşma ile etkileşim
- 🔄 **Gerçek Zamanlı** - WebSocket ile anlık yanıtlar
- 🧠 **Akıllı Planlama** - Seyahat planı oluşturma

## 🏗️ Mimari

```
┌─────────────┐     WebSocket     ┌──────────────┐
│  Frontend   │◄─────────────────►│   FastAPI    │
│  (HTML/JS)  │                   │   Server     │
└─────────────┘                   └──────┬───────┘
                                         │
                                  ┌──────▼───────┐
                                  │  LangGraph   │
                                  │    Agent     │
                                  └──────┬───────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
    ┌─────────▼─────────┐    ┌───────────▼───────────┐   ┌──────────▼──────────┐
    │  OpenWeatherMap   │    │   SerpAPI Hotels      │   │  SerpAPI Flights    │
    └───────────────────┘    └───────────────────────┘   └─────────────────────┘
```

## 🛠️ Teknolojiler

| Kategori | Teknoloji |
|----------|-----------|
| Backend | Python 3.11+, FastAPI, LangGraph, LangChain |
| Frontend | HTML5, CSS3, JavaScript, WebSocket |
| LLM | Groq API (GPT-oss-120b) |
| API'ler | OpenWeatherMap, SerpAPI (Google Hotels & Flights) |

## 📦 Kurulum

### 1. Repoyu klonlayın
```bash
git clone https://github.com/MSerkan-MOL/ai-travel-agent.git
cd ai-travel-agent
```

### 2. Sanal ortam oluşturun
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# veya
source .venv/bin/activate  # Linux/Mac
```

### 3. Bağımlılıkları yükleyin
```bash
pip install fastapi uvicorn langchain langchain-groq langgraph python-dotenv requests
```

### 4. API anahtarlarını ayarlayın
`.env` dosyası oluşturun:
```env
GROQ_API_KEY=your_groq_api_key
WEATHER_API_KEY=your_openweathermap_api_key
SERP_API_KEY=your_serpapi_key
```

### 5. Uygulamayı başlatın
```bash
python main.py
```

### 6. Tarayıcıda açın
```
http://localhost:8002
```

## 📁 Proje Yapısı

```
ai-travel-agent/
├── main.py           # FastAPI sunucu + LangGraph agent
├── tool.py           # API tool fonksiyonları
├── fast_api.py       # Alternatif API endpoint
├── .env              # API anahtarları (git'e eklenmez)
├── .gitignore        # Git ignore kuralları
├── pyproject.toml    # Proje bağımlılıkları
└── frontend/
    ├── index.html    # Ana sayfa + JavaScript
    └── style.css     # Stiller
```

## 🎯 Kullanım Örnekleri

```
"İstanbul'da hava durumu nasıl?"
"Paris'te 4 yıldızlı otel ara"
"İstanbul'dan Londra'ya 15 Ocak'ta uçuş bul"
"Bali için seyahat planı hazırla"
```

## 🔧 API Anahtarları Nasıl Alınır?

| API | Kayıt Linki |
|-----|-------------|
| Groq | https://console.groq.com/ |
| OpenWeatherMap | https://openweathermap.org/api |
| SerpAPI | https://serpapi.com/ |

## 📝 Lisans

Bu proje eğitim amaçlı geliştirilmiştir.

## 👤 Geliştirici

**MSerkan-MOL**
- GitHub: [@MSerkan-MOL](https://github.com/MSerkan-MOL)
