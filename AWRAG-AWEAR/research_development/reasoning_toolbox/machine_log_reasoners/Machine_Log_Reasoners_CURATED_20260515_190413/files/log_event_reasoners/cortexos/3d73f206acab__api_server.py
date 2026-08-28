import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from threat_analysis import ThreatAnalyzer

# Initialize FastAPI app
app = FastAPI(title="CortexEvolved Threat Detection API", version="1.0")

# Load AI-powered threat analyzer
analyzer = ThreatAnalyzer()

# Request Model for log entries
class LogEntry(BaseModel):
    log_text: str

@app.get("/")
def home():
    return {"message": "Welcome to CortexEvolved AI Security API"}

@app.post("/analyze")
def analyze_log(entry: LogEntry):
    """
    Analyze a security log entry using AI threat detection.
    """
    try:
        result = analyzer.analyze(entry.log_text)
        return {"log_text": entry.log_text, "threat_level": result["threat_level"], "confidence": result["confidence"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the API server when executed directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
