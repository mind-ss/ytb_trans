from flask import Flask, request, jsonify
import re
import json
import urllib.request
import urllib.parse
from collections import Counter
import xml.etree.ElementTree as ET

app = Flask(__name__)

def get_video_id(url):
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    else:
        raise ValueError("유효한 YouTube URL이 아닙니다.")

def get_transcript(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        html = urllib.request.urlopen(url).read().decode('utf-8')
        
        caption_url_match = re.search(r'"captionTracks":\s*(\[.*?\])', html)
        if not caption_url_match:
            raise ValueError("자막 정보를 찾을 수 없습니다.")
        
        caption_data = json.loads(caption_url_match.group(1))
        caption_url = None
        for item in caption_data:
            if item.get('languageCode') == 'ko':
                caption_url = item['baseUrl']
                break
        
        if not caption_url:
            raise ValueError("한국어 자막을 찾을 수 없습니다.")
        
        caption_xml = urllib.request.urlopen(caption_url).read().decode('utf-8')
        root = ET.fromstring(caption_xml)
        
        transcript = ' '.join(element.text for element in root.findall('.//text'))
        return transcript
    
    except Exception as e:
        return f"자막을 가져오는 데 실패했습니다: {str(e)}"

def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        html = urllib.request.urlopen(url).read().decode('utf-8')
        title_match = re.search(r'<title>(.*?)</title>', html)
        if title_match:
            return title_match.group(1).replace(" - YouTube", "")
        return "제목을 찾을 수 없습니다."
    except Exception as e:
        return f"제목을 가져오는 데 실패했습니다: {str(e)}"

def simple_summarize(text, num_sentences=5):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    words = re.findall(r'\w+', text.lower())
    word_freq = Counter(words)
    
    sentence_scores = []
    for sentence in sentences:
        score = sum(word_freq[word.lower()] for word in re.findall(r'\w+', sentence))
        sentence_scores.append((sentence, score))
    
    summary_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:num_sentences]
    summary_sentences.sort(key=lambda x: sentences.index(x[0]))
    
    return ' '.join(sentence for sentence, score in summary_sentences)

@app.route('/process', methods=['GET'])
def process_video():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL을 제공해주세요"}), 400
    
    try:
        video_id = get_video_id(url)
        title = get_video_title(video_id)
        transcript = get_transcript(video_id)

        if transcript.startswith("자막을 가져오는 데 실패했습니다"):
            return jsonify({"error": transcript}), 500

        summary = simple_summarize(transcript)

        return jsonify({
            "title": title,
            "transcript": transcript,
            "summary": summary
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
