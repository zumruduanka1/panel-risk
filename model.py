from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="savasy/bert-base-turkish-sentiment-cased"
)

def ai_score(text):
    try:
        res = classifier(text[:200])[0]

        # NEGATIVE → risk yüksek kabul ediyoruz
        if res["label"] == "negative":
            return min(90, int(res["score"] * 100))
        else:
            return int((1 - res["score"]) * 60)
    except:
        return 50