#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parent
TEMPLATE=ROOT/'templates'/'draftboard.html'
BACKUP=ROOT/'templates'/'draftboard.html.before-live-draft-mode'

STYLE='''<style id="live-draft-mode-styles">
.live-draft-bar{position:sticky;top:0;z-index:999;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;background:#172554;color:#fff;padding:10px 14px;margin:0 0 18px;border-radius:10px;box-shadow:0 3px 12px rgba(0,0,0,.18)}.live-draft-left,.live-draft-right{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.live-dot{width:10px;height:10px;border-radius:50%;background:#9ca3af;display:inline-block}.live-dot.connected{background:#22c55e;box-shadow:0 0 0 4px rgba(34,197,94,.18)}.live-dot.checking{background:#f59e0b}.live-dot.error{background:#ef4444}.live-pill{background:rgba(255,255,255,.12);padding:5px 9px;border-radius:999px;font-size:.82rem}.live-button{background:#fff;color:#172554;border:0;border-radius:6px;padding:7px 10px;font-weight:700;cursor:pointer}.live-button:hover{background:#e0e7ff}.live-draft-message{font-size:.86rem;color:#dbeafe}@media(max-width:700px){.live-draft-bar{position:static}.live-draft-left,.live-draft-right{width:100%;justify-content:space-between}}
</style>'''

BAR='''<div id="live-draft-bar" class="live-draft-bar" aria-live="polite">
<div class="live-draft-left"><span id="live-draft-dot" class="live-dot checking"></span><strong>Live Draft Mode</strong><span id="live-draft-status" class="live-pill">Starting...</span><span id="live-draft-picks" class="live-pill">Sleeper picks: --</span></div>
<div class="live-draft-right"><span id="live-draft-message" class="live-draft-message">Checking Sleeper</span><span id="live-draft-countdown" class="live-pill">Next check: --</span><button id="live-draft-toggle" class="live-button" type="button">Pause</button><button id="live-draft-refresh" class="live-button" type="button">Check now</button></div>
</div>'''

SCRIPT='''<script id="live-draft-mode-script">
(function(){
const endpoint="{{ url_for('test_draft_picks') }}",intervalSeconds=10;
const dot=document.getElementById("live-draft-dot"),status=document.getElementById("live-draft-status"),picksLabel=document.getElementById("live-draft-picks"),message=document.getElementById("live-draft-message"),countdown=document.getElementById("live-draft-countdown"),toggle=document.getElementById("live-draft-toggle"),refresh=document.getElementById("live-draft-refresh");
let enabled=localStorage.getItem("fiLiveDraftEnabled")!=="false",baseline=null,seconds=intervalSeconds,checking=false;
function setState(kind,label){dot.className="live-dot "+kind;status.textContent=label;}
function clock(){return new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"});}
function updateToggle(){toggle.textContent=enabled?"Pause":"Resume";countdown.textContent=enabled?"Next check: "+seconds+"s":"Paused";}
async function checkPicks(manual){if(checking||(!enabled&&!manual))return;checking=true;setState("checking","Checking");message.textContent="Contacting Sleeper...";try{const response=await fetch(endpoint,{cache:"no-store",headers:{"Accept":"application/json"}});if(!response.ok)throw new Error("HTTP "+response.status);const data=await response.json(),count=Array.isArray(data)?data.length:0;picksLabel.textContent="Sleeper picks: "+count;setState("connected",enabled?"Connected":"Paused");message.textContent="Last checked "+clock();if(baseline===null){baseline=count;}else if(count!==baseline){message.textContent="New Sleeper pick detected. Updating board...";localStorage.setItem("fiLastPickCount",String(count));window.setTimeout(function(){window.location.reload();},500);return;}baseline=count;seconds=intervalSeconds;}catch(error){setState("error","Connection issue");message.textContent="Sleeper check failed: "+error.message;seconds=intervalSeconds;}finally{checking=false;updateToggle();}}
toggle.addEventListener("click",function(){enabled=!enabled;localStorage.setItem("fiLiveDraftEnabled",String(enabled));if(enabled){seconds=0;setState("checking","Resuming");}else{setState("connected","Paused");message.textContent="Automatic checks paused";}updateToggle();});
refresh.addEventListener("click",function(){checkPicks(true);});updateToggle();checkPicks(true);window.setInterval(function(){if(!enabled)return;seconds-=1;if(seconds<=0){seconds=intervalSeconds;checkPicks(false);}updateToggle();},1000);
})();
</script>'''

def main():
    if not TEMPLATE.exists():
        print('Place this script in ~/fantasy-intelligence and run it there.')
        print('Expected templates/draftboard.html.')
        sys.exit(1)
    text=TEMPLATE.read_text(encoding='utf-8')
    if 'live-draft-mode-script' in text:
        print('Live Draft Mode is already installed.')
        return
    if '{% block content %}' not in text or '{% endblock %}' not in text:
        raise RuntimeError('Expected Jinja content block not found. No file changed.')
    updated=text.replace('{% block content %}','{% block content %}\n'+STYLE+'\n'+BAR,1)
    idx=updated.rfind('{% endblock %}')
    updated=updated[:idx]+SCRIPT+'\n'+updated[idx:]
    for token in ["url_for('test_draft_picks')",'fiLiveDraftEnabled','window.location.reload()','live-draft-toggle']:
        if token not in updated: raise RuntimeError('Generated template missing '+token)
    shutil.copy2(TEMPLATE,BACKUP)
    TEMPLATE.write_text(updated,encoding='utf-8')
    print('Live Draft Mode installed successfully.')
    print('Backup created: templates/draftboard.html.before-live-draft-mode')
    print('Sleeper picks will be checked every 10 seconds.')

if __name__=='__main__': main()
