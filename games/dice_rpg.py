"""Dice RPG — client game module (premium gacha tactical RPG).

Exposes get_css() and get_js(). The JS defines initDiceRpg(container), called by
showGame() in server.py. Catalog data + per-user state arrive from the server via
the dg_state WebSocket message (see games/dice_data.py for the data shape).

Phase 1/2: shell, dice-wall loading screen, home, and full Dex.
Later phases add the summon screen, team builder and combat engine.
"""


def get_css():
    return r"""
/* ============================ DICE RPG ============================ */
.dg-root{position:absolute;inset:0;display:flex;flex-direction:column;overflow:hidden;
  font-family:inherit;color:var(--text-primary);
  background:radial-gradient(1200px 600px at 50% -10%, rgba(123,97,255,0.12), transparent 60%),
             radial-gradient(900px 500px at 100% 110%, rgba(255,206,90,0.07), transparent 55%),
             var(--bg-primary);}
.dg-root *{box-sizing:border-box;}

/* rarity + element tokens */
.dg-root{--c-common:#5b8fd6;--c-rare:#a77bff;--c-mythic:#ffce5a;
  --e-Fire:#ff6b4a;--e-Ice:#5ad6ff;--e-Electric:#ffe14a;--e-Physical:#c9ccd6;--e-Arcane:#c47bff;}

/* ---- loading screen ---- */
.dg-loader{position:absolute;inset:0;z-index:40;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:26px;
  background:radial-gradient(900px 600px at 50% 40%, rgba(123,97,255,0.18), transparent 60%), #07070c;}
.dg-wall{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;width:min(380px,72vw);}
.dg-die-mini{aspect-ratio:1;display:flex;align-items:center;justify-content:center;
  font-size:26px;border-radius:9px;color:#cfd2ff;
  background:linear-gradient(160deg,#1a1b2e,#0d0e1a);border:1px solid rgba(123,97,255,0.25);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05);transition:opacity .5s,transform .5s;}
.dg-die-mini.fade{opacity:0;transform:scale(.4);}
.dg-converge{display:flex;gap:14px;}
.dg-big-die{width:62px;height:62px;display:flex;align-items:center;justify-content:center;
  font-size:46px;border-radius:14px;color:#fff;opacity:0;transform:translateY(24px) rotate(-18deg) scale(.6);
  background:linear-gradient(160deg,#2a2350,#14122a);border:1px solid rgba(167,123,255,.5);
  box-shadow:0 10px 30px rgba(123,97,255,.4),inset 0 1px 0 rgba(255,255,255,.12);
  animation:dgPop .55s cubic-bezier(.2,1.3,.4,1) forwards;}
@keyframes dgPop{to{opacity:1;transform:translateY(0) rotate(0) scale(1);}}
.dg-load-title{font-size:34px;font-weight:900;letter-spacing:7px;
  background:linear-gradient(90deg,#a77bff,#ffce5a);-webkit-background-clip:text;background-clip:text;
  color:transparent;opacity:0;transform:translateY(10px);transition:opacity .8s,transform .8s;}
.dg-load-sub{font-size:12px;color:#8a8aa8;letter-spacing:3px;text-transform:uppercase;
  opacity:0;transition:opacity .8s .2s;}
.dg-loader.ready .dg-load-title,.dg-loader.ready .dg-load-sub{opacity:1;transform:none;}

/* ---- top bar ---- */
.dg-top{display:flex;align-items:center;gap:14px;padding:12px 18px;
  background:linear-gradient(180deg,rgba(20,18,40,.85),rgba(20,18,40,.4));
  border-bottom:1px solid rgba(167,123,255,.18);backdrop-filter:blur(8px);z-index:5;}
.dg-logo{font-size:18px;font-weight:900;letter-spacing:3px;
  background:linear-gradient(90deg,#a77bff,#ffce5a);-webkit-background-clip:text;background-clip:text;color:transparent;}
.dg-nav{display:flex;gap:4px;margin-left:8px;flex-wrap:wrap;}
.dg-nav-btn{padding:7px 15px;border-radius:10px;border:1px solid transparent;cursor:pointer;
  background:transparent;color:var(--text-secondary);font-size:13px;font-weight:700;transition:all .15s;}
.dg-nav-btn:hover{color:var(--text-primary);background:rgba(167,123,255,.1);}
.dg-nav-btn.active{color:#fff;background:linear-gradient(160deg,rgba(167,123,255,.35),rgba(123,97,255,.18));
  border-color:rgba(167,123,255,.45);box-shadow:0 4px 14px rgba(123,97,255,.25);}
.dg-bal{margin-left:auto;display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px;
  padding:7px 14px;border-radius:11px;background:rgba(255,206,90,.1);border:1px solid rgba(255,206,90,.3);color:#ffd96b;}
.dg-bal .dg-coin{width:18px;height:18px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;
  font-size:11px;background:radial-gradient(circle at 35% 30%,#ffe9a8,#e0a93a);color:#5a3d00;font-weight:900;}

/* ---- content scroll area ---- */
.dg-body{flex:1;overflow-y:auto;padding:22px;scrollbar-width:thin;}
.dg-body::-webkit-scrollbar{width:8px;}
.dg-body::-webkit-scrollbar-thumb{background:rgba(167,123,255,.3);border-radius:4px;}

/* ---- home ---- */
.dg-hero{position:relative;border-radius:20px;overflow:hidden;padding:34px 30px;margin-bottom:22px;
  background:linear-gradient(120deg,rgba(42,35,80,.9),rgba(20,18,42,.7)),
    radial-gradient(600px 300px at 90% 20%,rgba(255,206,90,.18),transparent 60%);
  border:1px solid rgba(167,123,255,.25);}
.dg-hero h1{font-size:30px;font-weight:900;margin:0 0 8px;letter-spacing:1px;}
.dg-hero p{margin:0 0 20px;color:var(--text-secondary);max-width:560px;line-height:1.6;font-size:14px;}
.dg-cta{display:flex;gap:12px;flex-wrap:wrap;}
.dg-btn{padding:12px 22px;border-radius:12px;border:none;cursor:pointer;font-weight:800;font-size:14px;
  color:#fff;background:linear-gradient(160deg,#7b61ff,#5a3de0);box-shadow:0 8px 22px rgba(123,97,255,.35);
  transition:transform .12s,box-shadow .12s;}
.dg-btn:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(123,97,255,.5);}
.dg-btn.gold{background:linear-gradient(160deg,#ffce5a,#e0a93a);color:#3a2700;box-shadow:0 8px 22px rgba(255,206,90,.35);}
.dg-btn.ghost{background:rgba(255,255,255,.06);box-shadow:none;border:1px solid rgba(255,255,255,.14);}
.dg-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:22px;}
.dg-stat{padding:18px;border-radius:15px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);}
.dg-stat .v{font-size:26px;font-weight:900;}
.dg-stat .l{font-size:12px;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:1px;margin-top:2px;}
.dg-section-title{font-size:16px;font-weight:800;margin:8px 0 14px;display:flex;align-items:center;gap:8px;}

/* ---- dex ---- */
.dg-progress{display:flex;align-items:center;gap:14px;margin-bottom:18px;flex-wrap:wrap;}
.dg-pbar{flex:1;min-width:180px;height:10px;border-radius:6px;background:rgba(255,255,255,.08);overflow:hidden;}
.dg-pbar > i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,#a77bff,#ffce5a);}
.dg-filter{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;}
.dg-chip{padding:6px 13px;border-radius:20px;font-size:12px;font-weight:700;cursor:pointer;
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);color:var(--text-secondary);}
.dg-chip.active{background:rgba(167,123,255,.25);border-color:rgba(167,123,255,.5);color:#fff;}
.dg-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;}
.dg-card{position:relative;border-radius:16px;overflow:hidden;cursor:pointer;aspect-ratio:3/4;
  border:1px solid rgba(255,255,255,.1);transition:transform .14s,box-shadow .14s;
  background:linear-gradient(180deg,#1a1b2e,#101019);}
.dg-card:hover{transform:translateY(-4px);}
.dg-card.locked{filter:grayscale(1) brightness(.5);cursor:default;}
.dg-card.locked:hover{transform:none;}
.dg-card .dg-face{height:62%;display:flex;align-items:center;justify-content:center;font-size:54px;position:relative;}
.dg-card .dg-meta{padding:9px 10px;}
.dg-card .dg-nm{font-size:13px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.dg-card .dg-rl{font-size:11px;color:var(--text-tertiary);}
.dg-card.r-COMMON{box-shadow:inset 0 0 0 1px rgba(91,143,214,.4),0 6px 16px rgba(91,143,214,.12);}
.dg-card.r-RARE{box-shadow:inset 0 0 0 1px rgba(167,123,255,.5),0 6px 18px rgba(167,123,255,.18);}
.dg-card.r-MYTHIC{box-shadow:inset 0 0 0 1px rgba(255,206,90,.6),0 8px 22px rgba(255,206,90,.22);}
.dg-card.r-COMMON .dg-face{background:radial-gradient(circle at 50% 35%,rgba(91,143,214,.3),transparent 65%);}
.dg-card.r-RARE .dg-face{background:radial-gradient(circle at 50% 35%,rgba(167,123,255,.32),transparent 65%);}
.dg-card.r-MYTHIC .dg-face{background:radial-gradient(circle at 50% 35%,rgba(255,206,90,.34),transparent 65%);}
.dg-cons{position:absolute;top:8px;right:8px;font-size:10px;font-weight:900;padding:3px 7px;border-radius:8px;
  background:rgba(0,0,0,.55);color:#ffce5a;border:1px solid rgba(255,206,90,.4);}
.dg-elem{position:absolute;top:8px;left:8px;width:22px;height:22px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;font-size:11px;font-weight:900;background:rgba(0,0,0,.5);}
.dg-new{position:absolute;bottom:38%;left:8px;font-size:10px;font-weight:900;padding:2px 8px;border-radius:6px;
  background:#ff5470;color:#fff;letter-spacing:1px;}

/* ---- detail modal ---- */
.dg-modal{position:absolute;inset:0;z-index:50;display:flex;align-items:center;justify-content:center;
  background:rgba(4,4,10,.7);backdrop-filter:blur(6px);padding:20px;}
.dg-sheet{width:min(720px,96%);max-height:90%;overflow-y:auto;border-radius:20px;
  background:linear-gradient(180deg,#16162a,#0e0e1a);border:1px solid rgba(167,123,255,.3);
  box-shadow:0 30px 80px rgba(0,0,0,.6);scrollbar-width:thin;}
.dg-sheet-hd{display:flex;gap:18px;padding:24px;position:relative;
  background:radial-gradient(500px 200px at 80% 0%,rgba(167,123,255,.2),transparent 60%);}
.dg-portrait{width:120px;height:150px;border-radius:14px;display:flex;align-items:center;justify-content:center;
  font-size:72px;flex-shrink:0;background:linear-gradient(180deg,#22223c,#13131f);border:1px solid rgba(255,255,255,.1);}
.dg-sheet-hd h2{margin:0;font-size:24px;font-weight:900;}
.dg-tags{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0;}
.dg-tag{font-size:11px;font-weight:700;padding:3px 9px;border-radius:7px;background:rgba(255,255,255,.08);}
.dg-voice{font-style:italic;color:var(--text-secondary);margin-top:8px;font-size:13px;}
.dg-x{position:absolute;top:14px;right:16px;cursor:pointer;font-size:22px;color:var(--text-tertiary);
  background:none;border:none;line-height:1;}
.dg-sheet-bd{padding:0 24px 24px;}
.dg-statbars{display:grid;grid-template-columns:1fr 1fr;gap:10px 22px;margin:16px 0;}
.dg-sb{display:flex;flex-direction:column;gap:4px;}
.dg-sb .row{display:flex;justify-content:space-between;font-size:12px;font-weight:700;}
.dg-sb .bar{height:7px;border-radius:4px;background:rgba(255,255,255,.08);overflow:hidden;}
.dg-sb .bar > i{display:block;height:100%;background:linear-gradient(90deg,#7b61ff,#a77bff);}
.dg-lore{font-size:13px;line-height:1.65;color:var(--text-secondary);margin:14px 0;
  padding:14px;border-left:3px solid rgba(167,123,255,.5);background:rgba(167,123,255,.06);border-radius:0 10px 10px 0;}
.dg-ability{padding:13px 15px;border-radius:12px;background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.08);margin-bottom:10px;}
.dg-ability .ab-h{display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px;margin-bottom:5px;}
.dg-ability .ab-k{font-size:10px;font-weight:900;padding:2px 7px;border-radius:6px;text-transform:uppercase;letter-spacing:.5px;}
.dg-ability .ab-d{font-size:12px;color:var(--text-secondary);line-height:1.5;}
.dg-cons-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:8px;}
.dg-cons-item{font-size:11px;padding:9px 11px;border-radius:10px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);}
.dg-cons-item.on{border-color:rgba(255,206,90,.5);background:rgba(255,206,90,.08);color:#ffce5a;}

/* ---- generic placeholder ---- */
.dg-soon{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;
  height:60%;color:var(--text-tertiary);text-align:center;}
.dg-soon .big{font-size:54px;opacity:.5;}

/* ---- summon / banners ---- */
.dg-banner-tabs{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap;}
.dg-banner-tab{padding:9px 16px;border-radius:11px;cursor:pointer;font-weight:800;font-size:13px;
  background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);color:var(--text-secondary);transition:all .15s;}
.dg-banner-tab:hover{color:var(--text-primary);}
.dg-banner-tab.active{color:#fff;background:linear-gradient(160deg,rgba(167,123,255,.35),rgba(123,97,255,.18));
  border-color:rgba(167,123,255,.5);}
.dg-banner{border-radius:20px;overflow:hidden;border:1px solid rgba(167,123,255,.25);
  background:linear-gradient(180deg,#16162a,#0e0e1a);box-shadow:0 14px 40px rgba(0,0,0,.4);}
.dg-banner-art{position:relative;min-height:220px;display:flex;align-items:flex-end;padding:26px;
  background:radial-gradient(700px 320px at 80% 10%,rgba(167,123,255,.3),transparent 60%),
    linear-gradient(120deg,rgba(42,35,80,.6),rgba(20,18,42,.2));}
.dg-banner.b-limited .dg-banner-art{background:radial-gradient(700px 340px at 82% 6%,rgba(255,206,90,.34),transparent 58%),
    linear-gradient(125deg,rgba(70,46,30,.55),rgba(28,18,40,.3));}
.dg-banner.b-beginner .dg-banner-art{background:radial-gradient(700px 340px at 82% 6%,rgba(90,214,255,.28),transparent 58%),
    linear-gradient(125deg,rgba(24,52,70,.5),rgba(18,24,42,.3));}
.dg-banner-kicker{font-size:11px;font-weight:900;letter-spacing:2px;text-transform:uppercase;color:#ffce5a;margin-bottom:6px;}
.dg-banner-art h2{margin:0 0 6px;font-size:30px;font-weight:900;letter-spacing:.5px;}
.dg-banner-art p{margin:0;color:var(--text-secondary);font-size:13px;max-width:560px;line-height:1.55;}
.dg-feat{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap;}
.feat-chip{display:flex;align-items:center;gap:8px;padding:7px 11px 7px 8px;border-radius:11px;
  background:rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.12);}
.feat-chip.big{background:rgba(255,206,90,.12);}
.feat-chip .fc-face{font-size:24px;}
.feat-chip.big .fc-face{font-size:30px;}
.feat-chip .fc-nm{font-size:12px;font-weight:800;}
.dg-banner-foot{display:flex;align-items:flex-end;gap:20px;padding:20px 24px;flex-wrap:wrap;
  border-top:1px solid rgba(255,255,255,.07);background:rgba(0,0,0,.18);}
.dg-pity{flex:1;min-width:230px;}
.dg-pity .pity-row{display:flex;justify-content:space-between;font-size:12px;font-weight:700;margin-bottom:5px;}
.dg-pity .pity-row span:last-child{color:#ffd96b;}
.dg-pity .pity-tags{display:flex;gap:6px;margin-top:9px;flex-wrap:wrap;}
.dg-pity .pity-tag{font-size:11px;font-weight:800;padding:4px 10px;border-radius:8px;
  background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:var(--text-secondary);}
.dg-pity .pity-tag.done{background:rgba(123,224,140,.14);border-color:rgba(123,224,140,.4);color:#8fe6a0;}
.dg-pull-btns{display:flex;gap:10px;margin-left:auto;}
.dg-btn small{display:block;font-size:11px;font-weight:800;opacity:.85;margin-top:3px;}
.dg-btn:disabled{opacity:.4;cursor:not-allowed;transform:none;box-shadow:none;}
.dg-rates-note{margin-top:14px;font-size:12px;color:var(--text-tertiary);line-height:1.6;text-align:center;}

/* ---- pull animation overlay ---- */
.dg-pull-overlay{position:absolute;inset:0;z-index:60;display:flex;flex-direction:column;
  align-items:center;justify-content:center;background:radial-gradient(circle at 50% 45%,rgba(123,97,255,.18),rgba(4,4,10,.92));}
.dg-pull-overlay.r-RARE{background:radial-gradient(circle at 50% 45%,rgba(167,123,255,.3),rgba(4,4,10,.93));}
.dg-pull-overlay.r-MYTHIC{background:radial-gradient(circle at 50% 45%,rgba(255,206,90,.32),rgba(4,4,10,.94));}
.dg-pull-suspense{display:flex;flex-direction:column;align-items:center;gap:20px;}
.dg-roller{font-size:120px;color:#cfd2ff;text-shadow:0 0 36px rgba(167,123,255,.7);animation:dgRoll 1s linear infinite;}
@keyframes dgRoll{0%{transform:rotate(0) scale(1);}50%{transform:rotate(180deg) scale(1.12);}100%{transform:rotate(360deg) scale(1);}}
.dg-sus-txt{font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#9a9ac0;}
.dg-reveal-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;width:min(780px,94%);}
.dg-reveal-grid.single{grid-template-columns:1fr;width:auto;justify-items:center;}
.dg-reveal-card{opacity:0;transform:perspective(700px) rotateY(90deg);animation:dgFlip .5s cubic-bezier(.2,.9,.3,1) forwards;
  border-radius:14px;padding:14px 10px;text-align:center;background:linear-gradient(180deg,#1c1d31,#0e0e1a);
  border:1px solid rgba(255,255,255,.1);}
@keyframes dgFlip{to{opacity:1;transform:perspective(700px) rotateY(0);}}
.dg-reveal-card.r-RARE{box-shadow:0 0 0 1px rgba(167,123,255,.6),0 0 20px rgba(167,123,255,.35);}
.dg-reveal-card.r-MYTHIC{box-shadow:0 0 0 1px rgba(255,206,90,.75),0 0 28px rgba(255,206,90,.5);animation:dgFlip .5s cubic-bezier(.2,.9,.3,1) forwards,dgMythicPulse 1.6s ease-in-out .5s infinite;}
@keyframes dgMythicPulse{0%,100%{box-shadow:0 0 0 1px rgba(255,206,90,.75),0 0 22px rgba(255,206,90,.4);}50%{box-shadow:0 0 0 1px rgba(255,206,90,.9),0 0 36px rgba(255,206,90,.7);}}
.dg-reveal-card .rc-face{font-size:46px;position:relative;display:inline-block;}
.dg-reveal-grid.single .dg-reveal-card{width:240px;padding:30px;}
.dg-reveal-grid.single .rc-face{font-size:96px;}
.rc-nm{font-weight:800;font-size:13px;margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.rc-sub{font-size:11px;color:var(--text-tertiary);margin-top:3px;}
.rc-sub.isnew{color:#ff7a90;font-weight:900;letter-spacing:1px;}
.dg-reveal-foot{margin-top:26px;display:flex;gap:12px;}

/* ---- team builder ---- */
.dg-team-slots{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px;}
.dg-slot{position:relative;aspect-ratio:3/4;border-radius:16px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:6px;text-align:center;padding:10px;
  border:1px dashed rgba(255,255,255,.18);background:rgba(255,255,255,.025);}
.dg-slot.filled{border-style:solid;background:linear-gradient(180deg,#1a1b2e,#101019);}
.dg-slot.filled.r-RARE{border-color:rgba(167,123,255,.5);}
.dg-slot.filled.r-MYTHIC{border-color:rgba(255,206,90,.6);}
.dg-slot .slot-face{font-size:46px;}
.dg-slot .slot-nm{font-size:13px;font-weight:800;}
.dg-slot .slot-rl{font-size:11px;color:var(--text-tertiary);}
.dg-slot .slot-empty{font-size:30px;font-weight:900;color:rgba(255,255,255,.12);}
.dg-slot .slot-x{position:absolute;top:8px;right:9px;border:none;background:rgba(0,0,0,.5);color:#ff8097;
  border-radius:7px;width:22px;height:22px;cursor:pointer;font-size:14px;font-weight:900;line-height:1;}
.dg-team-bar{display:flex;align-items:center;gap:14px;margin-bottom:22px;font-weight:800;font-size:14px;}
.dg-team-bar > span{color:var(--text-secondary);}
.dg-team-bar .dg-btn{margin-left:auto;}
.dg-card.selected{outline:2px solid #ffce5a;outline-offset:1px;}
.dg-sel-badge{position:absolute;bottom:38%;right:8px;width:22px;height:22px;border-radius:50%;
  background:#ffce5a;color:#3a2700;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:13px;}

/* ---- history ---- */
.dg-hist{display:flex;flex-direction:column;gap:7px;}
.dg-hist-row{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:11px;
  background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.07);}
.dg-hist-row.r-RARE{border-color:rgba(167,123,255,.3);}
.dg-hist-row.r-MYTHIC{border-color:rgba(255,206,90,.4);background:rgba(255,206,90,.05);}
.dg-hist-row .hh-face{font-size:24px;width:28px;text-align:center;}
.dg-hist-row .nm{font-weight:800;font-size:14px;min-width:120px;}
.dg-hist-row .hh-rar{font-size:12px;font-weight:800;width:70px;}
.dg-hist-badge{font-size:10px;font-weight:900;padding:3px 8px;border-radius:7px;
  background:rgba(255,255,255,.08);color:var(--text-secondary);}
.dg-hist-badge.new{background:#ff5470;color:#fff;}
.dg-hist-row .hh-banner{font-size:11px;color:var(--text-tertiary);margin-left:auto;}
.dg-hist-row .hh-time{font-size:11px;color:var(--text-muted);min-width:104px;text-align:right;}

/* ---- battle hub (stage select) ---- */
.dg-hub-tabs{display:flex;gap:8px;margin-bottom:18px;}
.dg-stage{display:flex;align-items:center;gap:16px;padding:16px 18px;border-radius:15px;margin-bottom:12px;
  background:linear-gradient(120deg,rgba(28,26,52,.7),rgba(16,16,26,.5));border:1px solid rgba(255,255,255,.08);}
.dg-stage.cleared{border-color:rgba(123,224,140,.3);}
.dg-stage.locked{opacity:.5;}
.dg-stage .st-icon{width:54px;height:54px;border-radius:13px;display:flex;align-items:center;justify-content:center;
  font-size:30px;flex-shrink:0;background:radial-gradient(circle at 40% 30%,rgba(167,123,255,.4),rgba(20,18,40,.6));}
.dg-stage.t-ELITE .st-icon{background:radial-gradient(circle at 40% 30%,rgba(255,120,80,.45),rgba(40,18,20,.6));}
.dg-stage.t-BOSS .st-icon{background:radial-gradient(circle at 40% 30%,rgba(255,206,90,.5),rgba(40,28,8,.6));}
.dg-stage .st-body{flex:1;min-width:0;}
.dg-stage .st-nm{font-size:15px;font-weight:800;display:flex;align-items:center;gap:8px;}
.dg-stage .st-tier{font-size:10px;font-weight:900;padding:2px 7px;border-radius:6px;text-transform:uppercase;letter-spacing:.5px;
  background:rgba(167,123,255,.2);color:#c7b3ff;}
.dg-stage.t-ELITE .st-tier{background:rgba(255,120,80,.2);color:#ffb199;}
.dg-stage.t-BOSS .st-tier{background:rgba(255,206,90,.2);color:#ffd96b;}
.dg-stage .st-lore{font-size:12px;color:var(--text-tertiary);margin-top:4px;line-height:1.5;}
.dg-stage .st-go{flex-shrink:0;}
.dg-stage .st-done{flex-shrink:0;font-size:12px;font-weight:800;color:#8fe6a0;display:flex;align-items:center;gap:5px;}
.dg-reward-tag{font-size:11px;font-weight:800;color:#ffd96b;}

/* ---- battle arena ---- */
.dg-arena{display:flex;gap:16px;height:100%;}
.dg-arena-main{flex:1;display:flex;flex-direction:column;gap:16px;min-width:0;}
.dg-arena-side{width:268px;flex-shrink:0;display:flex;flex-direction:column;
  border-radius:15px;background:rgba(8,8,16,.6);border:1px solid rgba(255,255,255,.08);overflow:hidden;}
.dg-arena-side h4{margin:0;padding:12px 14px;font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#9a9ac0;
  border-bottom:1px solid rgba(255,255,255,.08);background:rgba(167,123,255,.08);}
.dg-log{flex:1;overflow-y:auto;padding:10px 12px;display:flex;flex-direction:column;gap:6px;scrollbar-width:thin;}
.dg-log::-webkit-scrollbar{width:6px;}.dg-log::-webkit-scrollbar-thumb{background:rgba(167,123,255,.3);border-radius:3px;}
.dg-log-line{font-size:12px;line-height:1.45;color:var(--text-secondary);padding-bottom:5px;border-bottom:1px dashed rgba(255,255,255,.05);}
.dg-log-line b{color:var(--text-primary);}
.dg-log-line.crit{color:#ffce5a;}.dg-log-line.heal{color:#8fe6a0;}
.dg-log-line.dmg b{color:#ff9a7a;}.dg-log-line.sys{color:#a77bff;font-weight:700;}
.dg-log-line.omen{color:#c47bff;}.dg-log-line.brk{color:#5ad6ff;}
.dg-battle-top{display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.dg-battle-top .bt-nm{font-size:17px;font-weight:900;}
.dg-battle-top .bt-rd{font-size:12px;color:var(--text-tertiary);}
.dg-battle-top .bt-actions{margin-left:auto;display:flex;gap:8px;}
.dg-mini-btn{padding:6px 12px;border-radius:9px;border:1px solid rgba(255,255,255,.14);cursor:pointer;
  background:rgba(255,255,255,.05);color:var(--text-secondary);font-size:12px;font-weight:700;}
.dg-mini-btn.on{background:rgba(167,123,255,.25);border-color:rgba(167,123,255,.5);color:#fff;}
.dg-side-group{flex:1;display:flex;flex-direction:column;gap:10px;justify-content:center;}
.dg-side-label{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-tertiary);font-weight:800;}
.dg-units{display:flex;flex-direction:column;gap:9px;}
.dg-units.enemies{}
.dg-unit{position:relative;padding:10px 12px;border-radius:13px;cursor:default;
  background:linear-gradient(120deg,rgba(30,28,54,.8),rgba(16,16,26,.6));border:1px solid rgba(255,255,255,.09);
  transition:transform .12s,box-shadow .12s,opacity .3s;}
.dg-unit.enemy{cursor:pointer;}
.dg-unit.enemy.target{border-color:#ff7a90;box-shadow:0 0 0 1px #ff7a90,0 0 16px rgba(255,90,112,.3);}
.dg-unit.active{border-color:#ffce5a;box-shadow:0 0 0 1px #ffce5a,0 0 18px rgba(255,206,90,.35);transform:translateX(3px);}
.dg-unit.dead{opacity:.32;filter:grayscale(1);}
.dg-unit.hit{animation:dgHit .3s;}
@keyframes dgHit{0%,100%{transform:translateX(0);}25%{transform:translateX(-6px);}75%{transform:translateX(6px);}}
.dg-unit-hd{display:flex;align-items:center;gap:9px;margin-bottom:7px;}
.dg-unit-glyph{font-size:24px;width:30px;text-align:center;flex-shrink:0;}
.dg-unit-nm{font-size:13px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.dg-unit-sub{font-size:10px;color:var(--text-tertiary);}
.dg-unit-el{margin-left:auto;font-size:10px;font-weight:900;padding:2px 7px;border-radius:6px;background:rgba(0,0,0,.4);flex-shrink:0;}
.dg-hpbar{height:9px;border-radius:5px;background:rgba(0,0,0,.45);overflow:hidden;position:relative;}
.dg-hpbar > i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#3fd17a,#7be08c);transition:width .35s;}
.dg-unit.enemy .dg-hpbar > i{background:linear-gradient(90deg,#ff5470,#ff8a5a);}
.dg-hptext{font-size:10px;color:var(--text-tertiary);margin-top:2px;display:flex;justify-content:space-between;}
.dg-enbar{height:5px;border-radius:3px;background:rgba(0,0,0,.4);overflow:hidden;margin-top:4px;}
.dg-enbar > i{display:block;height:100%;background:linear-gradient(90deg,#5ad6ff,#a77bff);transition:width .3s;}
.dg-tough{height:5px;border-radius:3px;background:rgba(0,0,0,.4);overflow:hidden;margin-top:4px;}
.dg-tough > i{display:block;height:100%;background:linear-gradient(90deg,#ffe14a,#5ad6ff);transition:width .3s;}
.dg-chips{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px;}
.dg-chip-s{font-size:9px;font-weight:900;padding:2px 6px;border-radius:5px;background:rgba(255,255,255,.08);color:var(--text-secondary);}
.dg-chip-s.omen{background:rgba(196,123,255,.2);color:#d3a8ff;}
.dg-chip-s.brk{background:rgba(90,214,255,.2);color:#9be4ff;}
.dg-chip-s.buff{background:rgba(123,224,140,.18);color:#8fe6a0;}
.dg-chip-s.deb{background:rgba(255,120,80,.2);color:#ffb199;}
.dg-chip-s.fort{background:rgba(255,206,90,.2);color:#ffd96b;}
.dg-actpanel{padding:14px 16px;border-radius:15px;background:rgba(8,8,16,.6);border:1px solid rgba(255,255,255,.1);
  display:flex;align-items:center;gap:12px;flex-wrap:wrap;min-height:64px;}
.dg-actpanel .ap-who{font-size:13px;font-weight:800;}
.dg-actpanel .ap-who small{display:block;font-weight:600;color:var(--text-tertiary);font-size:11px;}
.dg-act-btns{display:flex;gap:9px;margin-left:auto;flex-wrap:wrap;}
.dg-act{padding:10px 16px;border-radius:11px;border:none;cursor:pointer;font-weight:800;font-size:13px;color:#fff;
  background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);transition:transform .1s;}
.dg-act:hover:not(:disabled){transform:translateY(-2px);}
.dg-act.skill{background:linear-gradient(160deg,rgba(123,97,255,.5),rgba(90,60,224,.3));border-color:rgba(167,123,255,.5);}
.dg-act.ult{background:linear-gradient(160deg,#ffce5a,#e0a93a);color:#3a2700;border-color:rgba(255,206,90,.6);}
.dg-act:disabled{opacity:.4;cursor:not-allowed;}
.dg-act small{display:block;font-size:10px;font-weight:700;opacity:.85;}
.dg-result{position:absolute;inset:0;z-index:55;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;
  background:radial-gradient(circle at 50% 40%,rgba(123,97,255,.2),rgba(4,4,10,.92));text-align:center;padding:24px;}
.dg-result.win{background:radial-gradient(circle at 50% 40%,rgba(255,206,90,.28),rgba(4,4,10,.93));}
.dg-result h1{font-size:42px;font-weight:900;margin:0;letter-spacing:2px;
  background:linear-gradient(90deg,#a77bff,#ffce5a);-webkit-background-clip:text;background-clip:text;color:transparent;}
.dg-result .rs-reward{font-size:16px;font-weight:800;color:#ffd96b;}
.dg-fdmg{position:absolute;font-size:18px;font-weight:900;pointer-events:none;z-index:8;
  animation:dgFloat 1s ease-out forwards;text-shadow:0 2px 6px rgba(0,0,0,.7);}
@keyframes dgFloat{0%{opacity:0;transform:translateY(0) scale(.7);}20%{opacity:1;}100%{opacity:0;transform:translateY(-34px) scale(1.1);}}

@media(max-width:760px){.dg-arena{flex-direction:column;}.dg-arena-side{width:auto;height:200px;}}

/* ---- toast ---- */
.dg-toast{position:absolute;bottom:24px;left:50%;transform:translate(-50%,16px);z-index:70;
  padding:11px 20px;border-radius:11px;font-weight:800;font-size:13px;color:#fff;
  background:rgba(28,24,48,.96);border:1px solid rgba(167,123,255,.4);box-shadow:0 12px 30px rgba(0,0,0,.5);
  opacity:0;transition:opacity .25s,transform .25s;pointer-events:none;}
.dg-toast.show{opacity:1;transform:translate(-50%,0);}

@media(max-width:620px){.dg-reveal-grid{grid-template-columns:repeat(3,1fr);}
  .dg-team-slots{grid-template-columns:repeat(2,1fr);}
  .dg-hist-row .hh-banner{display:none;}}
@media(max-width:560px){.dg-sheet-hd{flex-direction:column;align-items:center;text-align:center;}
  .dg-statbars{grid-template-columns:1fr;}}

/* ===== v4.0 additions ===== */
/* wallet bar */
.dg-wallet{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-left:auto;}
.dg-cur{display:flex;align-items:center;gap:5px;padding:5px 11px;border-radius:10px;font-weight:800;font-size:12px;
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);}
.dg-cur .cur-i{font-size:13px;}
.dg-cur.gems{color:#ffd96b;border-color:rgba(255,206,90,.35);background:rgba(255,206,90,.08);}
.dg-cur.crystals{color:#9be4ff;border-color:rgba(90,214,255,.3);background:rgba(90,214,255,.07);}
.dg-cur.shards{color:#d3a8ff;border-color:rgba(196,123,255,.3);background:rgba(196,123,255,.07);}
.dg-cur.balance{color:var(--text-secondary);}
.dg-tools{display:flex;gap:6px;align-items:center;}
.dg-tool-btn{width:32px;height:32px;border-radius:9px;cursor:pointer;font-size:15px;line-height:1;
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);color:var(--text-secondary);}
.dg-tool-btn:hover{color:#fff;background:rgba(255,255,255,.1);}
.dg-mini{padding:5px 11px;border-radius:8px;border:1px solid rgba(255,255,255,.14);cursor:pointer;
  background:rgba(255,255,255,.05);color:var(--text-secondary);font-size:11px;font-weight:800;}
.dg-mini:hover:not(:disabled){color:#fff;background:rgba(255,255,255,.1);}
.dg-mini:disabled{opacity:.4;cursor:not-allowed;}
.dg-mini.gold{background:linear-gradient(160deg,#ffce5a,#e0a93a);color:#3a2700;border-color:rgba(255,206,90,.6);}
.dg-rates-note{font-size:12.5px;color:var(--text-secondary);line-height:1.6;margin-bottom:14px;
  padding:11px 14px;border-radius:11px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);}
/* convert cards */
.dg-convert{padding:15px 16px;border-radius:14px;margin-bottom:12px;
  background:linear-gradient(120deg,rgba(30,28,54,.6),rgba(16,16,26,.5));border:1px solid rgba(255,255,255,.1);}
.dg-convert .cv-h{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px;}
.dg-convert .cv-h b{font-size:15px;font-weight:900;}
.dg-convert .cv-h span{font-size:11px;color:var(--text-tertiary);}
.dg-convert .cv-row{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap;}
.dg-convert .cv-in{flex:1;min-width:120px;padding:9px 12px;border-radius:9px;font-size:14px;font-weight:700;
  background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.14);color:var(--text-primary);}
.dg-convert .cv-out{font-size:15px;font-weight:900;color:#ffd96b;}
.dg-convert .cv-quick{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;}
/* bundles */
.dg-bundles{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px;}
.dg-bundle{position:relative;padding:18px 16px;border-radius:16px;text-align:center;display:flex;flex-direction:column;gap:7px;
  background:linear-gradient(160deg,rgba(30,28,54,.7),rgba(14,14,24,.6));border:1px solid rgba(255,255,255,.1);}
.dg-bundle.best{border-color:rgba(255,206,90,.5);box-shadow:0 0 0 1px rgba(255,206,90,.25),0 10px 30px rgba(255,206,90,.1);}
.dg-bundle .bn-best{position:absolute;top:-9px;left:50%;transform:translateX(-50%);font-size:9px;font-weight:900;letter-spacing:1px;
  padding:3px 10px;border-radius:7px;background:linear-gradient(90deg,#ffce5a,#e0a93a);color:#3a2700;}
.dg-bundle .bn-icon{font-size:34px;}
.dg-bundle .bn-nm{font-size:15px;font-weight:900;}
.dg-bundle .bn-grant{font-size:13px;font-weight:800;color:#ffd96b;}
.dg-bundle .bn-desc{font-size:11px;color:var(--text-tertiary);line-height:1.5;flex:1;}
.dg-bundle .dg-btn{margin-top:4px;}
/* picks (bundle die select) */
.dg-picks{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;}
.dg-pick{display:flex;flex-direction:column;align-items:flex-start;gap:3px;padding:12px;border-radius:12px;cursor:pointer;text-align:left;
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);color:var(--text-primary);}
.dg-pick:hover{background:rgba(167,123,255,.15);border-color:rgba(167,123,255,.5);}
.dg-pick .pk-face{font-size:26px;}
.dg-pick .pk-nm{font-size:13px;font-weight:800;}
.dg-pick .pk-rl{font-size:10px;color:var(--text-tertiary);}
/* presets */
.dg-presets{display:flex;gap:10px;align-items:stretch;flex-wrap:wrap;margin-bottom:14px;}
.dg-presets-lbl{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--text-tertiary);font-weight:800;
  display:flex;align-items:center;}
.dg-preset{flex:1;min-width:150px;padding:9px 11px;border-radius:11px;
  background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);}
.dg-preset.filled{border-color:rgba(167,123,255,.3);}
.dg-preset .pr-no{font-size:10px;font-weight:800;color:var(--text-tertiary);}
.dg-preset .pr-faces{font-size:18px;min-height:24px;display:flex;gap:3px;align-items:center;}
.dg-preset .pr-btns{display:flex;gap:6px;margin-top:6px;}
/* comps */
.dg-comps{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin-bottom:8px;}
.dg-comp{padding:13px 14px;border-radius:14px;display:flex;flex-direction:column;gap:7px;
  background:linear-gradient(120deg,rgba(30,28,54,.55),rgba(16,16,26,.5));border:1px solid rgba(255,255,255,.1);}
.dg-comp .cmp-h{display:flex;align-items:center;gap:7px;}
.dg-comp .cmp-h b{font-size:14px;font-weight:900;}
.dg-comp .cmp-tag{font-size:9px;font-weight:900;letter-spacing:.5px;padding:2px 7px;border-radius:6px;
  background:rgba(167,123,255,.2);color:#d3a8ff;}
.dg-comp .cmp-d{font-size:11px;color:var(--text-tertiary);line-height:1.5;flex:1;}
.dg-comp .cmp-faces{display:flex;gap:6px;font-size:22px;}
.dg-comp .cmp-face.miss{opacity:.3;filter:grayscale(1);}
.dg-comp .cmp-own{font-size:10px;font-weight:800;color:var(--text-secondary);}
/* milestones + achievements rows */
.dg-miles,.dg-achs{display:flex;flex-direction:column;gap:9px;}
.dg-mile,.dg-ach{display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:12px;
  background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);}
.dg-mile.ready,.dg-ach.ready{border-color:rgba(255,206,90,.4);background:rgba(255,206,90,.06);}
.dg-mile.done,.dg-ach.done{opacity:.7;}
.dg-mile.locked,.dg-ach.locked{opacity:.55;}
.dg-mile .ml-wave{font-size:14px;font-weight:900;min-width:74px;}
.dg-mile .ml-rew,.dg-ach .ac-rew{font-size:12px;font-weight:800;color:#ffd96b;}
.dg-mile .ml-go,.dg-ach .ac-go{margin-left:auto;}
.ml-tick{font-size:11px;font-weight:800;color:#8fe6a0;}
.ml-lock{font-size:11px;color:var(--text-tertiary);}
.dg-ach .ac-icon{font-size:18px;width:26px;text-align:center;}
.dg-ach.done .ac-icon{color:#8fe6a0;}.dg-ach.ready .ac-icon{color:#ffce5a;}
.dg-ach .ac-body{flex:1;min-width:0;}
.dg-ach .ac-nm{font-size:14px;font-weight:800;}
.dg-ach .ac-desc{font-size:11px;color:var(--text-tertiary);}
/* ascension block in detail */
.dg-asc{margin-top:14px;padding:13px 14px;border-radius:12px;
  background:rgba(196,123,255,.07);border:1px solid rgba(196,123,255,.22);}
.dg-asc h4{margin:0 0 8px;font-size:13px;font-weight:900;}
.dg-asc .asc-row{display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:12px;}
.dg-asc .asc-grow{color:#8fe6a0;font-weight:800;}
.dg-asc .asc-btn{margin-top:10px;}
.cc-lv{font-size:11px;font-weight:800;color:#d3a8ff;}
/* turn-order timeline */
.dg-timeline{display:flex;align-items:center;gap:10px;margin:2px 0 4px;padding:8px 12px;border-radius:12px;
  background:rgba(8,8,16,.5);border:1px solid rgba(255,255,255,.08);}
.dg-timeline .tl-lbl{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--text-tertiary);font-weight:800;flex-shrink:0;}
.dg-timeline .tl-strip{display:flex;gap:7px;overflow-x:auto;}
.tl-pip{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);transition:transform .2s,box-shadow .2s;}
.tl-pip.enemy{border-color:rgba(255,120,144,.35);}
.tl-pip.now{border-color:#ffce5a;box-shadow:0 0 0 1px #ffce5a,0 0 12px rgba(255,206,90,.4);transform:translateY(-3px) scale(1.08);}
.tl-pip .tl-face{font-size:20px;}
.bt-phase{color:#ffd96b;font-weight:800;}
/* tutorial sections */
.tut-sec{display:flex;gap:13px;padding:13px 0;border-bottom:1px solid rgba(255,255,255,.07);}
.tut-sec:last-child{border-bottom:none;}
.tut-sec .tut-ic{font-size:26px;width:34px;text-align:center;flex-shrink:0;}
.tut-sec .tut-t{font-size:15px;font-weight:900;margin-bottom:4px;}
.tut-sec .tut-d{font-size:12.5px;color:var(--text-secondary);line-height:1.6;}
@media(max-width:620px){.dg-wallet .dg-cur.balance{display:none;}}
"""


def get_js():
    return r"""
function initDiceRpg(container){
  if(!container) return;
  container.innerHTML='';
  var root=document.createElement('div'); root.className='dg-root'; container.appendChild(root);

  var G={ catalog:null, dice:[], byId:{}, banners:{}, K:{}, state:null, bal:0,
          view:'home', dexFilter:'ALL', timers:[], ready:false, minDone:false,
          banner:'limited', teamDraft:null, pulling:false, pullOverlay:null, rollTimer:null,
          shopTab:'wallet', speed:1, muted:false, achTab:null, presetDraft:null,
          selectBundle:null };
  try{ G.muted = localStorage.getItem('dg_muted')==='1';
       var sp=parseFloat(localStorage.getItem('dg_speed')); if(sp===0.75||sp===1||sp===1.5) G.speed=sp; }catch(e){}

  var DIE_FACES=['\u2680','\u2681','\u2682','\u2683','\u2684','\u2685'];
  function elemColor(e){return getComputedStyle(root).getPropertyValue('--e-'+e)||'#fff';}
  function fmt(n){return Math.floor(n||0).toLocaleString();}
  function rarColor(r){return r==='MYTHIC'?'#ffce5a':r==='RARE'?'#a77bff':'#5b8fd6';}
  function dieGlyph(id){ // stable glyph from id hash
    var h=0; for(var i=0;i<id.length;i++) h=(h*31+id.charCodeAt(i))%6; return DIE_FACES[h]; }

  function dgSend(obj){ try{ if(window.ws && window.ws.readyState===1) window.ws.send(JSON.stringify(obj)); }catch(e){} }

  /* ---------- loading screen ---------- */
  var loader=document.createElement('div'); loader.className='dg-loader'; root.appendChild(loader);
  var wall=document.createElement('div'); wall.className='dg-wall'; loader.appendChild(wall);
  var minis=[];
  for(var i=0;i<42;i++){ var s=document.createElement('div'); s.className='dg-die-mini';
    s.textContent=DIE_FACES[(Math.random()*6)|0]; wall.appendChild(s); minis.push(s); }
  var flick=setInterval(function(){ for(var j=0;j<minis.length;j++){ if(Math.random()<0.5)
    minis[j].textContent=DIE_FACES[(Math.random()*6)|0]; } }, 90);
  G.timers.push(flick);
  G.timers.push(setTimeout(function(){
    clearInterval(flick);
    for(var k=0;k<minis.length;k++){ (function(m,idx){ setTimeout(function(){ m.classList.add('fade'); }, idx*14); })(minis[k],k); }
  },1500));
  G.timers.push(setTimeout(function(){
    wall.className='dg-converge';
    wall.innerHTML='';
    for(var b=0;b<6;b++){ var d=document.createElement('div'); d.className='dg-big-die';
      d.style.animationDelay=(b*0.09)+'s'; d.textContent=DIE_FACES[b]; wall.appendChild(d); }
    var t=document.createElement('div'); t.className='dg-load-title'; t.textContent='DICE  RPG'; loader.appendChild(t);
    var sub=document.createElement('div'); sub.className='dg-load-sub'; sub.textContent='The House Always Wins'; loader.appendChild(sub);
    setTimeout(function(){ loader.classList.add('ready'); },120);
  },2150));
  G.timers.push(setTimeout(function(){ G.minDone=true; tryShow(); },3300));

  function tryShow(){ if(G.minDone && G.ready){ loader.style.transition='opacity .5s';
    loader.style.opacity='0'; setTimeout(function(){ if(loader.parentNode) loader.parentNode.removeChild(loader); },520);
    buildShell(); render(); } }

  /* request data */
  dgSend({type:'dg_get_state'});
  // safety retry
  G.timers.push(setTimeout(function(){ if(!G.ready) dgSend({type:'dg_get_state'}); },2600));

  /* ---------- message handler ---------- */
  window._diceMessageHandler=function(d){
    if(d.type==='dg_state'){
      G.catalog=d.catalog; G.dice=d.catalog.dice; G.banners=d.catalog.banners; G.K=d.catalog.constants;
      G.byId={}; G.dice.forEach(function(x){ G.byId[x.id]=x; });
      G.state=d.state; G.bal=d.balance||0;
      G.ready=true; tryShow();
      if(loader.parentNode===null || !document.body.contains(loader)) { updateBal(); if(G.view) render(); }
    } else if(d.type==='dg_pull_result'){
      if(window._dgOnPull) window._dgOnPull(d);
    } else if(d.type==='dg_team_result'){
      if(d.ok && G.state){ G.state.team=d.team||G.state.team; }
    } else if(d.type==='dg_reward_result'){
      if(window._dgOnReward) window._dgOnReward(d);
    } else if(d.type==='dg_convert_result'){
      applyMut(d, d.ok?('Converted \u2014 +'+fmt(d.gained)+(d.direction==='to_gems'?' Gems':' Crystals')):null);
    } else if(d.type==='dg_bundle_result'){
      var bm = d.ok ? (d.grant_kind ? (d.grant_kind==='new'?'New die added!':d.grant_kind==='constellation'?'Duplicate \u2014 Constellation up!':'Already maxed \u2014 Universal Shards added.') : ('Purchased \u2014 +'+fmt(d.gems_added)+' Gems')) : null;
      G.selectBundle=null; applyMut(d, bm);
    } else if(d.type==='dg_milestone_result'){
      applyMut(d, d.ok&&!d.already?('Milestone claimed!'):null); if(d.already) toast('Already claimed.');
    } else if(d.type==='dg_ascend_result'){
      applyMut(d, d.ok?('Ascended to A'+d.level+'!'):null);
    } else if(d.type==='dg_achievement_result'){
      applyMut(d, d.ok&&!d.already?('Reward claimed!'):null); if(d.already) toast('Already claimed.');
    } else if(d.type==='dg_presets_result'){
      if(d.ok){ if(d.state) G.state=d.state; toast('Presets saved.'); }
      else toast((d&&d.error)||'Save failed.');
    }
  };
  function applyMut(d, okMsg){
    if(!d){ return; }
    if(d.state) G.state=d.state;
    if(typeof d.balance==='number') G.bal=d.balance;
    updateBal();
    if(!d.ok){ toast(d.error||'Something went wrong.'); render(); return; }
    if(okMsg) toast(okMsg);
    sfx('ok'); render();
  }

  /* ---------- shell ---------- */
  var bodyEl, balEl, navBtns={};
  function buildShell(){
    var top=document.createElement('div'); top.className='dg-top';
    var logo=document.createElement('div'); logo.className='dg-logo'; logo.textContent='\u2684 DICE RPG'; top.appendChild(logo);
    var nav=document.createElement('div'); nav.className='dg-nav';
    [['home','Home'],['summon','Summon'],['shop','Shop'],['battle','Battle'],['team','Team'],['dex','Dex'],['achievements','Goals'],['history','History']].forEach(function(p){
      var b=document.createElement('button'); b.className='dg-nav-btn'; b.textContent=p[1];
      b.onclick=function(){ G.view=p[0]; render(); };
      nav.appendChild(b); navBtns[p[0]]=b;
    });
    top.appendChild(nav);
    balEl=document.createElement('div'); balEl.className='dg-wallet';
    balEl.innerHTML=
      '<div class="dg-cur c-gem" title="Gems \u2014 used for summons and ascension"><span class="dg-coin gem">\u25C6</span><span class="v-gem">0</span></div>'+
      '<div class="dg-cur c-cry" title="Crystals \u2014 buy bundles, convert to Gems"><span class="dg-coin cry">\u2756</span><span class="v-cry">0</span></div>'+
      '<div class="dg-cur c-shd" title="Universal Shards \u2014 ascend your dice"><span class="dg-coin shd">\u269C</span><span class="v-shd">0</span></div>'+
      '<div class="dg-cur c-bal" title="Balance \u2014 your chat economy"><span class="dg-coin">$</span><span class="v-bal">0</span></div>';
    top.appendChild(balEl);
    var tools=document.createElement('div'); tools.className='dg-tools';
    var tut=document.createElement('button'); tut.className='dg-tool-btn'; tut.title='How to play'; tut.textContent='?';
    tut.onclick=openTutorial; tools.appendChild(tut);
    var mute=document.createElement('button'); mute.className='dg-tool-btn'; mute.id='dgMute';
    mute.title='Sound'; mute.textContent=G.muted?'\uD83D\uDD07':'\uD83D\uDD0A';
    mute.onclick=function(){ G.muted=!G.muted; try{localStorage.setItem('dg_muted',G.muted?'1':'0');}catch(e){}
      mute.textContent=G.muted?'\uD83D\uDD07':'\uD83D\uDD0A'; if(!G.muted) sfx('ok'); };
    tools.appendChild(mute); top.appendChild(tools);
    root.appendChild(top);
    bodyEl=document.createElement('div'); bodyEl.className='dg-body'; root.appendChild(bodyEl);
    updateBal();
    if(!tutorialSeen()) G.timers.push(setTimeout(openTutorial,400));
  }
  function wallet(){ return (G.state&&G.state.gacha)||{}; }
  function updateBal(){
    if(!balEl) return; var w=wallet();
    var g=balEl.querySelector('.v-gem'); if(g) g.textContent=fmt(w.gems||0);
    var c=balEl.querySelector('.v-cry'); if(c) c.textContent=fmt(w.crystals||0);
    var s=balEl.querySelector('.v-shd'); if(s) s.textContent=fmt(w.universal_shards||0);
    var b=balEl.querySelector('.v-bal'); if(b) b.textContent=fmt(G.bal);
  }
  /* ---------- sound ---------- */
  var _actx=null;
  function sfx(kind){
    if(G.muted) return;
    try{ _actx=_actx||new (window.AudioContext||window.webkitAudioContext)();
      var seq={ok:[660],hit:[180],crit:[520,780],ult:[440,660,880],win:[523,659,784,1046],lose:[330,247,165]}[kind]||[440];
      var t=_actx.currentTime;
      seq.forEach(function(f,i){ var o=_actx.createOscillator(),g=_actx.createGain();
        o.type=(kind==='ult'||kind==='win')?'triangle':'sine'; o.frequency.value=f;
        var st=t+i*0.07; g.gain.setValueAtTime(0.0001,st);
        g.gain.exponentialRampToValueAtTime(0.16,st+0.01);
        g.gain.exponentialRampToValueAtTime(0.0001,st+0.12);
        o.connect(g); g.connect(_actx.destination); o.start(st); o.stop(st+0.14); });
    }catch(e){}
  }

  function render(){
    if(!bodyEl) return;
    for(var k in navBtns) navBtns[k].classList.toggle('active',k===G.view);
    if(G.view!=='team') G.teamDraft=null;
    updateBal();
    bodyEl.innerHTML='';
    if(G.view==='home') renderHome();
    else if(G.view==='dex') renderDex();
    else if(G.view==='summon') renderSummon();
    else if(G.view==='shop') renderShop();
    else if(G.view==='battle') renderBattleHub();
    else if(G.view==='team') renderTeam();
    else if(G.view==='achievements') renderAchievements();
    else if(G.view==='history') renderHistory();
  }

  /* ---------- shared helpers ---------- */
  function capit(s){ s=String(s||''); return s.charAt(0)+s.slice(1).toLowerCase(); }
  function bestRarity(results){ var best='COMMON';
    results.forEach(function(r){ if(r.rarity==='MYTHIC') best='MYTHIC'; else if(r.rarity==='RARE'&&best!=='MYTHIC') best='RARE'; });
    return best; }
  function toast(msg){
    var t=document.createElement('div'); t.className='dg-toast'; t.textContent=msg; root.appendChild(t);
    requestAnimationFrame(function(){ t.classList.add('show'); });
    G.timers.push(setTimeout(function(){ t.classList.remove('show');
      setTimeout(function(){ if(t.parentNode) t.remove(); },300); },2100));
  }

  /* ---------- home ---------- */
  function ownedCount(){ return G.state?Object.keys(G.state.collection||{}).length:0; }
  function renderHome(){
    var total=G.dice.length, owned=ownedCount();
    var g=G.state.gacha||{};
    var hero=document.createElement('div'); hero.className='dg-hero';
    hero.innerHTML='<h1>Welcome to the Table</h1>'+
      '<p>Summon Dice, forge a team of fate, and gamble against the House across a story campaign and an endless arena. Every roll is loaded \u2014 the only question is in whose favor.</p>'+
      '<div class="dg-cta">'+
        '<button class="dg-btn gold" data-go="summon">\u2684 Summon Dice</button>'+
        '<button class="dg-btn" data-go="battle">\u2694 Enter Campaign</button>'+
        '<button class="dg-btn ghost" data-go="dex">\u2630 Open Dex</button>'+
      '</div>';
    bodyEl.appendChild(hero);
    hero.querySelectorAll('[data-go]').forEach(function(b){ b.onclick=function(){ G.view=b.getAttribute('data-go'); render(); }; });

    var stats=document.createElement('div'); stats.className='dg-stats';
    function stat(v,l){ return '<div class="dg-stat"><div class="v">'+v+'</div><div class="l">'+l+'</div></div>'; }
    stats.innerHTML=stat(owned+' / '+total,'Dice Owned')+stat(fmt(g.total_pulls||0),'Total Summons')+
      stat(fmt(G.bal),'Balance')+stat(fmt(g.universal_shards||0),'Universal Shards');
    bodyEl.appendChild(stats);

    var st=document.createElement('div'); st.className='dg-section-title'; st.textContent='Featured Banner'; bodyEl.appendChild(st);
    var lim=G.banners.limited;
    var card=document.createElement('div'); card.className='dg-hero'; card.style.marginBottom='0';
    card.innerHTML='<h1 style="font-size:22px">'+lim.name+'</h1><p>'+lim.subtitle+'</p>'+
      '<div class="dg-cta"><button class="dg-btn gold" data-go="summon">Summon Now</button></div>';
    bodyEl.appendChild(card);
    card.querySelector('[data-go]').onclick=function(){ G.view='summon'; render(); };
  }

  /* ---------- dex ---------- */
  function renderDex(){
    var total=G.dice.length, owned=ownedCount();
    var head=document.createElement('div');
    var prog=document.createElement('div'); prog.className='dg-progress';
    prog.innerHTML='<b>Collection</b><div class="dg-pbar"><i style="width:'+(total?owned/total*100:0)+'%"></i></div>'+
      '<span style="font-weight:800">'+owned+' / '+total+'</span>';
    bodyEl.appendChild(prog);

    var filt=document.createElement('div'); filt.className='dg-filter';
    [['ALL','All'],['MYTHIC','Mythic'],['RARE','Rare'],['COMMON','Common'],['OWNED','Owned'],['MISSING','Missing']].forEach(function(f){
      var c=document.createElement('span'); c.className='dg-chip'+(G.dexFilter===f[0]?' active':''); c.textContent=f[1];
      c.onclick=function(){ G.dexFilter=f[0]; renderDex_refresh(); };
      filt.appendChild(c);
    });
    bodyEl.appendChild(filt);

    var grid=document.createElement('div'); grid.className='dg-grid'; grid.id='dgDexGrid'; bodyEl.appendChild(grid);
    fillDex(grid);
  }
  function renderDex_refresh(){ bodyEl.innerHTML=''; renderDex(); }
  function fillDex(grid){
    var coll=G.state.collection||{};
    G.dice.forEach(function(die){
      var own=!!coll[die.id]; var f=G.dexFilter;
      if(f==='OWNED'&&!own) return; if(f==='MISSING'&&own) return;
      if(f==='MYTHIC'||f==='RARE'||f==='COMMON'){ if(die.rarity!==f) return; }
      var card=document.createElement('div'); card.className='dg-card r-'+die.rarity+(own?'':' locked');
      var cons=own?(coll[die.id].constellation||0):0;
      card.innerHTML=
        '<div class="dg-face" style="color:'+rarColor(die.rarity)+'">'+(own?dieGlyph(die.id):'?')+
          '<span class="dg-elem" style="color:'+elemColor(die.element)+'">'+die.element.charAt(0)+'</span>'+
          (own&&cons>0?'<span class="dg-cons">C'+cons+'</span>':'')+
        '</div>'+
        '<div class="dg-meta"><div class="dg-nm">'+(own?die.name:'???')+'</div>'+
        '<div class="dg-rl">'+(own?die.rarity.charAt(0)+die.rarity.slice(1).toLowerCase()+' \u2022 '+die.role:'Undiscovered')+'</div></div>';
      if(own) card.onclick=function(){ openDetail(die); };
      grid.appendChild(card);
    });
  }

  /* ---------- detail modal ---------- */
  function openDetail(die){
    var coll=G.state.collection||{}; var cons=(coll[die.id]&&coll[die.id].constellation)||0;
    var modal=document.createElement('div'); modal.className='dg-modal';
    modal.onclick=function(e){ if(e.target===modal) modal.remove(); };
    var st=die.stats;
    var maxStat={hp:1500,atk:170,def:130,spd:125};
    function bar(label,key){ var v=st[key]; var pct=Math.min(100,v/maxStat[key]*100);
      return '<div class="dg-sb"><div class="row"><span>'+label+'</span><span>'+v+'</span></div>'+
        '<div class="bar"><i style="width:'+pct+'%"></i></div></div>'; }
    function ability(k,a,color){ if(!a) return '';
      return '<div class="dg-ability"><div class="ab-h"><span class="ab-k" style="background:'+color+'22;color:'+color+'">'+k+'</span>'+a.name+'</div>'+
        '<div class="ab-d">'+a.desc+'</div></div>'; }
    var consHtml='';
    (G.K.CONSTELLATION_BONUS||[]).forEach(function(c){
      consHtml+='<div class="dg-cons-item'+(cons>=c.level?' on':'')+'"><span class="cc-lv">C'+c.level+'</span><span>'+c.desc+'</span></div>'; });
    var owned=!!coll[die.id], lvl=(coll[die.id]&&coll[die.id].level)||0, maxLvl=G.K.ASCENSION_MAX_LEVEL||6;
    var shards=wallet().universal_shards||0, steps=(G.K.ASCENSION_STEP_COST||{})[die.rarity]||[];
    var nextCost = lvl<maxLvl ? steps[lvl] : null;
    var ascPct=Math.round(lvl*(G.K.ASCENSION_STAT_PER_LEVEL||0.06)*100);
    var ascHtml='<div class="dg-section-title" style="margin-top:18px">Ascension <span style="font-weight:600;color:var(--text-muted);font-size:11px">\u2014 Universal Shards \u2192 flat stats</span></div>'+
      '<div class="dg-asc"><div class="asc-info">Level <b>A'+lvl+'</b> / A'+maxLvl+'  \u2022  +'+ascPct+'% HP / ATK / DEF</div>'+
      '<div class="asc-bar"><i style="width:'+(lvl/maxLvl*100)+'%"></i></div>'+
      (owned ? (lvl<maxLvl ? '<button class="dg-btn gold asc-btn">Ascend \u2014 \u269C '+nextCost+'</button>'
                           : '<div class="asc-max">\u2605 Fully Ascended</div>')
             : '<div class="asc-max" style="color:var(--text-muted)">Summon this die to ascend it.</div>')+
      '</div>';
    var sheet=document.createElement('div'); sheet.className='dg-sheet';
    sheet.innerHTML=
      '<div class="dg-sheet-hd">'+
        '<button class="dg-x">\u00D7</button>'+
        '<div class="dg-portrait" style="color:'+rarColor(die.rarity)+'">'+dieGlyph(die.id)+'</div>'+
        '<div><h2>'+die.name+'</h2>'+
          '<div class="dg-tags"><span class="dg-tag" style="color:'+rarColor(die.rarity)+'">'+die.rarity+'</span>'+
          '<span class="dg-tag" style="color:'+elemColor(die.element)+'">'+die.element+'</span>'+
          '<span class="dg-tag">'+die.role+'</span>'+(cons>0?'<span class="dg-tag" style="color:#ffce5a">C'+cons+'</span>':'')+'</div>'+
          '<div class="dg-voice">'+die.voice+'</div></div>'+
      '</div>'+
      '<div class="dg-sheet-bd">'+
        '<div class="dg-lore">'+die.lore+'</div>'+
        '<div class="dg-statbars">'+bar('HP','hp')+bar('ATK','atk')+bar('DEF','def')+bar('SPD','spd')+'</div>'+
        ability('Basic',die.basic,'#9aa3b8')+ability('Skill',die.skill,'#a77bff')+
        ability('Ultimate',die.ult,'#ffce5a')+ability('Passive',die.passive,'#5ad6ff')+
        ascHtml+
        '<div class="dg-section-title" style="margin-top:18px">Constellations <span style="font-weight:600;color:var(--text-muted);font-size:11px">\u2014 utility effects, not extra damage</span></div>'+
        '<div class="dg-cons-list">'+consHtml+'</div>'+
      '</div>';
    modal.appendChild(sheet); root.appendChild(modal);
    sheet.querySelector('.dg-x').onclick=function(){ modal.remove(); };
    var ab=sheet.querySelector('.asc-btn');
    if(ab){ if(shards<nextCost){ ab.disabled=true; ab.title='Need '+nextCost+' Universal Shards'; }
      ab.onclick=function(){ if(shards<nextCost){ toast('Not enough Universal Shards.'); return; }
        dgSend({type:'dg_ascend', die_id:die.id}); modal.remove(); }; }
  }

  /* ---------- summon ---------- */
  function bannerKicker(bid){ return bid==='limited'?'Limited Banner':bid==='beginner'?'Beginner Banner':'Standard Banner'; }
  function featChip(die,big){
    if(!die) return '';
    return '<div class="feat-chip'+(big?' big':'')+'" style="border-color:'+rarColor(die.rarity)+'66">'+
      '<span class="fc-face" style="color:'+rarColor(die.rarity)+'">'+dieGlyph(die.id)+'</span>'+
      '<span class="fc-nm">'+die.name+'</span></div>';
  }
  function pityBox(bid,g){
    var box=document.createElement('div'); box.className='dg-pity';
    if(bid==='beginner'){
      var used=g.beginner_pulls||0, max=G.K.BEGINNER_MAX_PULLS||50;
      box.innerHTML='<div class="pity-row"><span>Beginner Pulls</span><span>'+used+' / '+max+'</span></div>'+
        '<div class="dg-pbar"><i style="width:'+Math.min(100,used/max*100)+'%"></i></div>'+
        '<div class="pity-tags"><span class="pity-tag'+(g.beg_rare_secured?' done':'')+'">Rare by 10</span>'+
        '<span class="pity-tag'+(g.beg_mythic_secured?' done':'')+'">Mythic by 40</span></div>';
    } else {
      var pm=g.pity_mythic||0, pr=g.pity_rare||0, hard=89;
      var rareIn=10-(pr%10); if(rareIn>10) rareIn=10;
      var fifty = bid==='limited' ? (g.limited_guarantee?'Next Mythic: Featured GUARANTEED':'Next Mythic: 50/50') : '';
      box.innerHTML='<div class="pity-row"><span>Mythic Soft Pity</span><span>'+pm+' / '+hard+'</span></div>'+
        '<div class="dg-pbar"><i style="width:'+Math.min(100,pm/hard*100)+'%"></i></div>'+
        '<div class="pity-row" style="margin-top:9px"><span>Guaranteed Rare in</span><span>'+rareIn+' pull'+(rareIn===1?'':'s')+'</span></div>'+
        (fifty?'<div class="pity-tags"><span class="pity-tag'+(g.limited_guarantee?' done':'')+'">'+fifty+'</span></div>':'');
    }
    return box;
  }
  function renderSummon(){
    var g=G.state.gacha||{};
    var avail=['limited','standard'];
    if(!g.beginner_done) avail.unshift('beginner');
    if(avail.indexOf(G.banner)<0) G.banner=avail[0];
    var tabs=document.createElement('div'); tabs.className='dg-banner-tabs';
    avail.forEach(function(bid){
      var b=G.banners[bid];
      var t=document.createElement('button'); t.className='dg-banner-tab'+(G.banner===bid?' active':'');
      t.textContent=b.name; t.onclick=function(){ G.banner=bid; renderSummon_refresh(); };
      tabs.appendChild(t);
    });
    bodyEl.appendChild(tabs);

    var bid=G.banner, b=G.banners[bid];
    var card=document.createElement('div'); card.className='dg-banner b-'+bid;
    var featHtml='';
    if(bid==='limited'){
      featHtml='<div class="dg-feat">'+featChip(G.byId[b.featured_mythic],true)+
        (b.featured_rares||[]).map(function(id){ return featChip(G.byId[id],false); }).join('')+'</div>';
    }
    card.innerHTML='<div class="dg-banner-art"><div>'+
      '<div class="dg-banner-kicker">'+bannerKicker(bid)+'</div>'+
      '<h2>'+b.name+'</h2><p>'+b.subtitle+'</p>'+featHtml+'</div></div>';
    var foot=document.createElement('div'); foot.className='dg-banner-foot';
    foot.appendChild(pityBox(bid,g));
    var cost1=(bid==='beginner'?G.K.BEGINNER_PULL_COST:G.K.PULL_COST), cost10=cost1*10;
    var gems=wallet().gems||0;
    var btns=document.createElement('div'); btns.className='dg-pull-btns';
    btns.innerHTML='<button class="dg-btn ghost" data-c="1">\u2684 \u00D71<small>\u25C6 '+cost1+'</small></button>'+
      '<button class="dg-btn gold" data-c="10">\u2684 \u00D710<small>\u25C6 '+cost10+'</small></button>';
    foot.appendChild(btns); card.appendChild(foot);
    bodyEl.appendChild(card);
    btns.querySelectorAll('[data-c]').forEach(function(btn){
      var c=parseInt(btn.getAttribute('data-c'),10), cost=c*cost1;
      if(gems<cost) btn.disabled=true;
      btn.onclick=function(){ doPull(bid,c); };
    });
    if(gems<cost1){
      var lo=document.createElement('div'); lo.className='dg-rates-note';
      lo.innerHTML='Low on Gems? <a href="#" style="color:#ffd96b;font-weight:800">Convert in the Shop \u2192</a>';
      lo.querySelector('a').onclick=function(e){ e.preventDefault(); G.view='shop'; G.shopTab='wallet'; render(); };
      foot.appendChild(lo);
    }

    var note=document.createElement('div'); note.className='dg-rates-note';
    note.innerHTML='Rates \u2014 Mythic 1% \u2022 Rare 5% \u2022 Common 94%. Mythic soft pity rises from pull 70, guaranteed by 89. Every 10th summon is at least Rare.'+
      (bid==='limited'?'<br>Win the 50/50 for the featured Mythic; lose it and the next Mythic is guaranteed featured.':'')+
      (bid==='beginner'?'<br>First 50 summons only, 20% off, with a guaranteed Rare within 10 and a Mythic within 40.':'')+
      '<br>Duplicates become Constellations (C1\u2013C6), then convert to Universal Shards.';
    bodyEl.appendChild(note);
  }
  function renderSummon_refresh(){ bodyEl.innerHTML=''; renderSummon(); }

  /* ---------- pull animation ---------- */
  function doPull(bid,count){
    if(G.pulling) return;
    var cost=(bid==='beginner'?G.K.BEGINNER_PULL_COST:G.K.PULL_COST)*count;
    if((wallet().gems||0)<cost){ toast('Not enough Gems \u2014 convert in the Shop.'); return; }
    G.pulling=true;
    dgSend({type:'dg_pull', banner:bid, count:count});
    showPullSuspense();
  }
  function showPullSuspense(){
    var ov=document.createElement('div'); ov.className='dg-pull-overlay';
    ov.innerHTML='<div class="dg-pull-suspense"><div class="dg-roller">\u2684</div>'+
      '<div class="dg-sus-txt">Rolling the dice\u2026</div></div>';
    root.appendChild(ov); G.pullOverlay=ov; G.pullStart=Date.now();
    var roller=ov.querySelector('.dg-roller');
    G.rollTimer=setInterval(function(){ roller.textContent=DIE_FACES[(Math.random()*6)|0]; },110);
    G.timers.push(G.rollTimer);
  }
  function revealPulls(results){
    var best=bestRarity(results);
    var wait=Math.max(0, 950-(Date.now()-(G.pullStart||0)));
    G.timers.push(setTimeout(function(){ doReveal(results,best); }, wait));
  }
  function doReveal(results,best){
    var ov=G.pullOverlay; if(!ov) return;
    if(G.rollTimer){ clearInterval(G.rollTimer); G.rollTimer=null; }
    ov.className='dg-pull-overlay r-'+best;
    ov.innerHTML='';
    var grid=document.createElement('div');
    grid.className='dg-reveal-grid'+(results.length>1?'':' single');
    ov.appendChild(grid);
    results.forEach(function(r,i){
      var die=G.byId[r.id]||{name:r.id,element:'Arcane'};
      var c=document.createElement('div'); c.className='dg-reveal-card r-'+r.rarity;
      c.style.animationDelay=(i*0.11)+'s';
      var sub=r.new?'NEW':(r.shards?('+'+r.shards+' Shards'):('C'+r.cons));
      c.innerHTML='<div class="rc-face" style="color:'+rarColor(r.rarity)+'">'+dieGlyph(r.id)+
        '<span class="dg-elem" style="color:'+elemColor(die.element)+'">'+String(die.element||'?').charAt(0)+'</span></div>'+
        '<div class="rc-nm">'+(die.name||r.id)+'</div>'+
        '<div class="rc-sub'+(r.new?' isnew':'')+'">'+sub+'</div>';
      grid.appendChild(c);
    });
    var foot=document.createElement('div'); foot.className='dg-reveal-foot';
    var done=document.createElement('button'); done.className='dg-btn gold'; done.textContent='Done';
    done.onclick=closePull; foot.appendChild(done);
    ov.appendChild(foot);
    ov.onclick=function(e){ if(e.target===ov) closePull(); };
  }
  function closePull(){
    if(G.rollTimer){ clearInterval(G.rollTimer); G.rollTimer=null; }
    if(G.pullOverlay){ G.pullOverlay.remove(); G.pullOverlay=null; }
    G.pulling=false; render();
  }
  window._dgOnPull=function(d){
    if(!d || !d.ok){ G.pulling=false;
      if(G.rollTimer){ clearInterval(G.rollTimer); G.rollTimer=null; }
      if(G.pullOverlay){ G.pullOverlay.remove(); G.pullOverlay=null; }
      toast((d&&d.error)||'Summon failed.'); return; }
    if(d.state) G.state=d.state;
    if(typeof d.balance==='number'){ G.bal=d.balance; updateBal(); }
    revealPulls(d.results||[]);
  };

  /* ---------- team builder ---------- */
  function renderTeam(){
    var coll=G.state.collection||{}, max=G.K.TEAM_SIZE||4;
    if(G.teamDraft==null) G.teamDraft=(G.state.team||[]).filter(function(id){ return coll[id]; }).slice(0,max);
    var draft=G.teamDraft;
    var slotsWrap=document.createElement('div'); slotsWrap.className='dg-team-slots';
    for(var i=0;i<max;i++){
      var id=draft[i];
      var slot=document.createElement('div');
      if(id && G.byId[id]){ var die=G.byId[id];
        slot.className='dg-slot filled r-'+die.rarity;
        slot.innerHTML='<button class="slot-x">\u00D7</button>'+
          '<div class="slot-face" style="color:'+rarColor(die.rarity)+'">'+dieGlyph(id)+'</div>'+
          '<div class="slot-nm">'+die.name+'</div><div class="slot-rl">'+die.role+'</div>';
        (function(theId){ slot.querySelector('.slot-x').onclick=function(e){ e.stopPropagation(); toggleTeam(theId); }; })(id);
      } else {
        slot.className='dg-slot';
        slot.innerHTML='<div class="slot-empty">'+(i+1)+'</div>';
      }
      slotsWrap.appendChild(slot);
    }
    bodyEl.appendChild(slotsWrap);

    var bar=document.createElement('div'); bar.className='dg-team-bar';
    bar.innerHTML='<span>'+draft.length+' / '+max+' selected</span>';
    var save=document.createElement('button'); save.className='dg-btn gold'; save.textContent='Save Team';
    save.onclick=saveTeam; bar.appendChild(save);
    bodyEl.appendChild(bar);

    renderPresets();
    renderComps(coll);

    var title=document.createElement('div'); title.className='dg-section-title';
    title.textContent='Your Dice'; bodyEl.appendChild(title);
    var owned=G.dice.filter(function(d){ return coll[d.id]; });
    if(!owned.length){
      var e=document.createElement('div'); e.className='dg-soon';
      e.innerHTML='<div class="big">\u2684</div><p>No dice yet \u2014 summon some first!</p>';
      bodyEl.appendChild(e); return;
    }
    var order={MYTHIC:0,RARE:1,COMMON:2};
    owned.sort(function(a,b){ return (order[a.rarity]-order[b.rarity]) || a.name.localeCompare(b.name); });
    var grid=document.createElement('div'); grid.className='dg-grid'; bodyEl.appendChild(grid);
    owned.forEach(function(die){
      var sel=draft.indexOf(die.id)>=0, cons=coll[die.id].constellation||0;
      var card=document.createElement('div'); card.className='dg-card r-'+die.rarity+(sel?' selected':'');
      card.innerHTML='<div class="dg-face" style="color:'+rarColor(die.rarity)+'">'+dieGlyph(die.id)+
        '<span class="dg-elem" style="color:'+elemColor(die.element)+'">'+die.element.charAt(0)+'</span>'+
        (cons>0?'<span class="dg-cons">C'+cons+'</span>':'')+
        (sel?'<span class="dg-sel-badge">\u2713</span>':'')+
        '</div><div class="dg-meta"><div class="dg-nm">'+die.name+'</div>'+
        '<div class="dg-rl">'+capit(die.rarity)+' \u2022 '+die.role+'</div></div>';
      card.onclick=function(){ toggleTeam(die.id); };
      grid.appendChild(card);
    });
  }
  function renderTeam_refresh(){ bodyEl.innerHTML=''; renderTeam(); }
  function toggleTeam(id){
    if(G.teamDraft==null) G.teamDraft=[];
    var i=G.teamDraft.indexOf(id), max=G.K.TEAM_SIZE||4;
    if(i>=0){ G.teamDraft.splice(i,1); }
    else { if(G.teamDraft.length>=max){ toast('Team is full ('+max+').'); return; } G.teamDraft.push(id); }
    renderTeam_refresh();
  }
  function saveTeam(){
    if(!G.teamDraft || !G.teamDraft.length){ toast('Pick at least one die.'); return; }
    dgSend({type:'dg_set_team', team:G.teamDraft.slice()});
    if(G.state) G.state.team=G.teamDraft.slice();
    toast('Team saved.');
  }
  function presets(){ return ((G.state.campaign&&G.state.campaign.presets)||[]); }
  function renderPresets(){
    var slots=G.K.TEAM_PRESET_SLOTS||3, ps=presets();
    var wrap=document.createElement('div'); wrap.className='dg-presets';
    var lbl=document.createElement('div'); lbl.className='dg-presets-lbl'; lbl.textContent='Presets'; wrap.appendChild(lbl);
    for(var i=0;i<slots;i++){
      (function(idx){
        var saved=ps[idx]||[];
        var cell=document.createElement('div'); cell.className='dg-preset'+(saved.length?' filled':'');
        var faces=saved.map(function(id){ var d=G.byId[id]; return d?'<span style="color:'+rarColor(d.rarity)+'">'+dieGlyph(id)+'</span>':''; }).join('');
        cell.innerHTML='<div class="pr-no">Slot '+(idx+1)+'</div><div class="pr-faces">'+(faces||'<span style="color:var(--text-muted)">empty</span>')+'</div>';
        var btns=document.createElement('div'); btns.className='pr-btns';
        var load=document.createElement('button'); load.className='dg-mini'; load.textContent='Load';
        load.disabled=!saved.length; load.onclick=function(){ loadPreset(idx); };
        var sv=document.createElement('button'); sv.className='dg-mini gold'; sv.textContent='Save';
        sv.onclick=function(){ savePreset(idx); };
        btns.appendChild(load); btns.appendChild(sv); cell.appendChild(btns);
        wrap.appendChild(cell);
      })(i);
    }
    bodyEl.appendChild(wrap);
  }
  function loadPreset(i){
    var p=(presets()[i]||[]).filter(function(id){ return (G.state.collection||{})[id]; });
    if(!p.length){ toast('That preset is empty.'); return; }
    G.teamDraft=p.slice(0,G.K.TEAM_SIZE||4); renderTeam_refresh(); toast('Preset '+(i+1)+' loaded \u2014 Save Team to use it.');
  }
  function savePreset(i){
    if(!G.teamDraft||!G.teamDraft.length){ toast('Pick a team first.'); return; }
    var slots=G.K.TEAM_PRESET_SLOTS||3, ps=presets().slice();
    while(ps.length<slots) ps.push([]);
    ps[i]=G.teamDraft.slice();
    if(G.state&&G.state.campaign) G.state.campaign.presets=ps;
    dgSend({type:'dg_save_presets', presets:ps});
    renderTeam_refresh();
  }
  function renderComps(coll){
    var comps=G.K.TEAM_COMPS||[]; if(!comps.length) return;
    var t=document.createElement('div'); t.className='dg-section-title'; t.textContent='Recommended Comps'; bodyEl.appendChild(t);
    var wrap=document.createElement('div'); wrap.className='dg-comps';
    comps.forEach(function(c){
      var core=(c.core||[]).concat(c.flex?[c.flex]:[]);
      var owned=core.filter(function(id){ return coll[id]; }).length;
      var card=document.createElement('div'); card.className='dg-comp';
      var faces=core.map(function(id){ var d=G.byId[id]; var have=!!coll[id];
        return '<span class="cmp-face'+(have?'':' miss')+'" title="'+((d&&d.name)||id)+(have?'':' (not owned)')+'" style="color:'+(d?rarColor(d.rarity):'#555')+'">'+dieGlyph(id)+'</span>'; }).join('');
      card.innerHTML='<div class="cmp-h"><span class="cmp-tag">'+c.primary+'</span><b>'+c.name+'</b></div>'+
        '<div class="cmp-d">'+c.desc+'</div><div class="cmp-faces">'+faces+'</div>'+
        '<div class="cmp-own">'+owned+' / '+core.length+' owned</div>';
      var use=document.createElement('button'); use.className='dg-mini gold'; use.textContent='Try This';
      use.onclick=function(){ var pick=core.filter(function(id){ return coll[id]; }).slice(0,G.K.TEAM_SIZE||4);
        if(!pick.length){ toast('You don\u2019t own any dice from this comp yet.'); return; }
        G.teamDraft=pick; renderTeam_refresh(); toast('Loaded what you own from '+c.name+'.'); };
      card.appendChild(use); wrap.appendChild(card);
    });
    bodyEl.appendChild(wrap);
  }

  /* ---------- history ---------- */
  function renderHistory(){
    var hist=(G.state.history||[]).slice().reverse(), g=G.state.gacha||{};
    var m=0,r=0; hist.forEach(function(h){ if(h.rarity==='MYTHIC')m++; else if(h.rarity==='RARE')r++; });
    var stats=document.createElement('div'); stats.className='dg-stats';
    function stat(v,l){ return '<div class="dg-stat"><div class="v">'+v+'</div><div class="l">'+l+'</div></div>'; }
    stats.innerHTML=stat(fmt(g.total_pulls||0),'Total Summons')+stat(m,'Mythics Shown')+
      stat(r,'Rares Shown')+stat(fmt(g.universal_shards||0),'Universal Shards');
    bodyEl.appendChild(stats);
    if(!hist.length){ renderSoon('History','\u23F3','No summons yet \u2014 visit the altar!'); return; }
    var wrap=document.createElement('div'); wrap.className='dg-hist'; bodyEl.appendChild(wrap);
    hist.forEach(function(h){
      var die=G.byId[h.id]||{name:h.id};
      var row=document.createElement('div'); row.className='dg-hist-row r-'+h.rarity;
      var badge=h.new?'<span class="dg-hist-badge new">NEW</span>':
        (h.shards?'<span class="dg-hist-badge">+'+h.shards+' shards</span>':'<span class="dg-hist-badge">C'+h.cons+'</span>');
      row.innerHTML='<span class="hh-face" style="color:'+rarColor(h.rarity)+'">'+dieGlyph(h.id)+'</span>'+
        '<span class="nm">'+die.name+'</span>'+
        '<span class="hh-rar" style="color:'+rarColor(h.rarity)+'">'+capit(h.rarity)+'</span>'+
        badge+'<span class="hh-banner">'+capit(h.banner)+'</span>'+
        '<span class="hh-time">'+(h.t||'')+'</span>';
      wrap.appendChild(row);
    });
  }

  /* ================= COMBAT ENGINE ================= */
  var SCALE=8;
  var ELEM_ADV={Fire:'Ice',Ice:'Electric',Electric:'Physical',Physical:'Arcane',Arcane:'Fire'};
  var CAMPAIGN=[
    {id:'c1',name:'The Felt Tables',tier:'NORMAL',
     lore:'Below the casino floor, the cheapest tables run themselves. The dice that lost here never left.',
     enemies:[
       {name:'Pip Thug',element:'Physical',hp:1450,atk:112,def:46,spd:94,pow:1.0,ai:'basic'},
       {name:'Pip Thug',element:'Electric',hp:1450,atk:112,def:46,spd:90,pow:1.0,ai:'basic'},
       {name:'Table Runner',element:'Fire',hp:1300,atk:120,def:40,spd:108,pow:1.05,ai:'basic'}]},
    {id:'c2',name:'Crooked Hall',tier:'NORMAL',
     lore:'Marked decks, weighted chips, smiling staff. Everything here is rigged \u2014 and it still wants more.',
     enemies:[
       {name:'Card Sharp',element:'Arcane',hp:1600,atk:124,def:54,spd:112,pow:1.05,ai:'debuff'},
       {name:'Card Sharp',element:'Ice',hp:1600,atk:124,def:54,spd:104,pow:1.05,ai:'basic'},
       {name:'House Marker',element:'Physical',hp:1750,atk:118,def:70,spd:88,pow:1.1,ai:'basic'}]},
    {id:'c3',name:'The Pit Boss',tier:'ELITE',
     lore:'He has watched a thousand gamblers go bust. He intends to make you the thousand and first.',
     enemies:[
       {name:'Enforcer',element:'Fire',hp:2100,atk:138,def:74,spd:100,pow:1.1,ai:'basic'},
       {name:'Pit Boss',element:'Physical',hp:4200,atk:158,def:104,spd:96,pow:1.25,ai:'aoe'},
       {name:'Enforcer',element:'Electric',hp:2100,atk:138,def:74,spd:103,pow:1.1,ai:'basic'}]},
    {id:'c4',name:'Vault Approach',tier:'NORMAL',
     lore:'The closer you get to the money, the colder the air, the heavier the dice.',
     enemies:[
       {name:'Vault Guard',element:'Ice',hp:1900,atk:128,def:82,spd:92,pow:1.1,ai:'basic'},
       {name:'Vault Guard',element:'Physical',hp:1900,atk:128,def:82,spd:90,pow:1.1,ai:'debuff'},
       {name:'Alarm Die',element:'Electric',hp:1500,atk:134,def:58,spd:124,pow:1.05,ai:'aoe'}]},
    {id:'c5',name:'The Croupier Twins',tier:'ELITE',
     lore:'Two dealers, one fate. They finish each other\u2019s hands \u2014 and your run.',
     enemies:[
       {name:'Croupier Noir',element:'Arcane',hp:3600,atk:150,def:90,spd:114,pow:1.2,ai:'debuff'},
       {name:'Croupier Blanc',element:'Fire',hp:3600,atk:150,def:90,spd:113,pow:1.2,ai:'heal'}]},
    {id:'c6',name:'The House Edge',tier:'BOSS',
     lore:'The owner of every outcome. It does not cheat \u2014 it simply already knows how this ends. Prove it wrong.',
     enemies:[
       {name:'Loaded Shill',element:'Electric',hp:3200,atk:150,def:88,spd:118,pow:1.1,ai:'basic'},
       {name:'The House',element:'Arcane',hp:16000,atk:182,def:130,spd:108,pow:1.35,ai:'boss'},
       {name:'Loaded Shill',element:'Fire',hp:3200,atk:150,def:88,spd:115,pow:1.1,ai:'basic'}]}
  ];
  function campIndex(id){ for(var i=0;i<CAMPAIGN.length;i++) if(CAMPAIGN[i].id===id) return i; return -1; }
  function clearedList(){ return (G.state.campaign&&G.state.campaign.cleared)||[]; }
  function tierGlyph(t){ return t==='BOSS'?'\u265B':t==='ELITE'?'\u265E':'\u265F'; }

  /* ---------- battle hub (stage select) ---------- */
  function renderBattleHub(){
    var B=G.battle;
    if(B && B.live){ renderBattle(); return; }
    var tabs=document.createElement('div'); tabs.className='dg-hub-tabs';
    [['campaign','Campaign'],['endless','Endless Arena']].forEach(function(p){
      var b=document.createElement('button'); b.className='dg-banner-tab'+((G.hubTab||'campaign')===p[0]?' active':'');
      b.textContent=p[1]; b.onclick=function(){ G.hubTab=p[0]; bodyEl.innerHTML=''; renderBattleHub(); };
      tabs.appendChild(b);
    });
    bodyEl.appendChild(tabs);
    var teamReady=(G.state.team||[]).filter(function(id){ return (G.state.collection||{})[id]; }).length>0;
    if(!teamReady){
      var w=document.createElement('div'); w.className='dg-soon';
      w.innerHTML='<div class="big">\u2694</div><h2 style="margin:0">Set a Team First</h2>'+
        '<p>Summon some dice, then build a team in the Team tab before you fight.</p>';
      var go=document.createElement('button'); go.className='dg-btn gold'; go.style.marginTop='14px';
      go.textContent='Go to Team'; go.onclick=function(){ G.view='team'; render(); };
      w.appendChild(go); bodyEl.appendChild(w); return;
    }
    if((G.hubTab||'campaign')==='campaign') renderCampaignList();
    else renderEndless();
  }
  function renderCampaignList(){
    var cleared=clearedList(), rew=(G.K.BATTLE_FIRST_CLEAR_REWARD||50);
    CAMPAIGN.forEach(function(st,idx){
      var done=cleared.indexOf(st.id)>=0;
      var locked=idx>0 && cleared.indexOf(CAMPAIGN[idx-1].id)<0;
      var row=document.createElement('div'); row.className='dg-stage t-'+st.tier+(done?' cleared':'')+(locked?' locked':'');
      var right = done? '<div class="st-done">\u2713 Cleared</div>'
        : locked? '<div class="st-done" style="color:var(--text-muted)">\uD83D\uDD12 Locked</div>'
        : '';
      row.innerHTML='<div class="st-icon">'+tierGlyph(st.tier)+'</div>'+
        '<div class="st-body"><div class="st-nm">'+st.name+
          '<span class="st-tier">'+st.tier+'</span>'+
          (done?'':'<span class="dg-reward-tag">First clear +'+rew+'</span>')+'</div>'+
          '<div class="st-lore">'+st.lore+'</div></div>';
      var slot=document.createElement('div'); slot.className='st-go'; slot.innerHTML=right; row.appendChild(slot);
      if(!locked){
        var btn=document.createElement('button'); btn.className='dg-btn '+(done?'ghost':'gold');
        btn.textContent=done?'Replay':'Fight'; btn.onclick=function(){ startBattle('campaign',st); };
        slot.innerHTML=''; slot.appendChild(btn);
        if(done){ var tag=document.createElement('div'); tag.className='st-done'; tag.style.marginTop='6px';
          tag.innerHTML='\u2713'; }
      }
      bodyEl.appendChild(row);
    });
  }
  function renderEndless(){
    var best=(G.state.campaign&&G.state.campaign.best_wave)||0;
    var sc=G.K.ENDLESS_SCALE||{};
    var card=document.createElement('div'); card.className='dg-stage t-ELITE';
    card.innerHTML='<div class="st-icon">\u267E</div>'+
      '<div class="st-body"><div class="st-nm">Endless Arena<span class="st-tier">SURVIVE</span></div>'+
      '<div class="st-lore">Endless waves of the House\u2019s enforcers. Each wave enemies gain +'+Math.round((sc.hp_per_wave||0.2)*100)+'% HP and +'+Math.round((sc.atk_per_wave||0.12)*100)+'% ATK. Every 3rd wave is an Elite, every 5th a Boss. Best wave reached: <b>'+best+'</b>.</div></div>';
    var slot=document.createElement('div'); slot.className='st-go';
    var btn=document.createElement('button'); btn.className='dg-btn gold'; btn.textContent='Enter';
    btn.onclick=function(){ startBattle('endless',null); };
    slot.appendChild(btn); card.appendChild(slot);
    bodyEl.appendChild(card);

    var ms=G.K.ENDLESS_MILESTONES||[];
    if(ms.length){
      var claimed=(G.state.campaign&&G.state.campaign.milestones)||[];
      var t=document.createElement('div'); t.className='dg-section-title'; t.textContent='Milestone Rewards'; bodyEl.appendChild(t);
      var wrap=document.createElement('div'); wrap.className='dg-miles';
      ms.forEach(function(m){
        var done=claimed.indexOf(m.wave)>=0, reached=best>=m.wave;
        var rew=[]; if(m.gems) rew.push('\u25C6 '+m.gems); if(m.crystals) rew.push('\u2756 '+m.crystals); if(m.shards) rew.push('\u269C '+m.shards);
        var row=document.createElement('div'); row.className='dg-mile'+(done?' done':reached?' ready':' locked');
        row.innerHTML='<div class="ml-wave">Wave '+m.wave+'</div><div class="ml-rew">'+rew.join('  \u2022  ')+'</div>';
        var go=document.createElement('div'); go.className='ml-go';
        if(done){ go.innerHTML='<span class="ml-tick">\u2713 Claimed</span>'; }
        else if(reached){ var b=document.createElement('button'); b.className='dg-mini gold'; b.textContent='Claim';
          b.onclick=function(){ dgSend({type:'dg_claim_milestone', wave:m.wave}); }; go.appendChild(b); }
        else { go.innerHTML='<span class="ml-lock">Reach wave '+m.wave+'</span>'; }
        row.appendChild(go); wrap.appendChild(row);
      });
      bodyEl.appendChild(wrap);
    }
  }

  /* ================= SHOP (convert + bundles) ================= */
  function renderShop(){
    var tabs=document.createElement('div'); tabs.className='dg-hub-tabs';
    [['wallet','Convert'],['bundles','Bundles']].forEach(function(p){
      var b=document.createElement('button'); b.className='dg-banner-tab'+((G.shopTab||'wallet')===p[0]?' active':'');
      b.textContent=p[1]; b.onclick=function(){ G.shopTab=p[0]; bodyEl.innerHTML=''; renderShop(); };
      tabs.appendChild(b);
    });
    bodyEl.appendChild(tabs);
    if((G.shopTab||'wallet')==='wallet') renderWallet(); else renderBundles();
  }
  function convertCard(title, sub, dir, maxAmt, rate, fromGlyph, toGlyph){
    var card=document.createElement('div'); card.className='dg-convert';
    card.innerHTML='<div class="cv-h"><b>'+title+'</b><span>'+sub+'</span></div>'+
      '<div class="cv-row"><input type="number" class="cv-in" min="1" placeholder="Amount" />'+
      '<div class="cv-out">\u2192 <span class="cv-get">0</span> '+toGlyph+'</div></div>'+
      '<div class="cv-quick"></div>';
    var inp=card.querySelector('.cv-in'), out=card.querySelector('.cv-get'), quick=card.querySelector('.cv-quick');
    function calc(){ var v=Math.max(0,Math.floor(parseFloat(inp.value)||0)); out.textContent=fmt(Math.floor(v*rate)); return v; }
    inp.oninput=calc;
    [100,500,'Max'].forEach(function(q){
      var b=document.createElement('button'); b.className='dg-mini'; b.textContent=q==='Max'?'Max':('+'+q);
      b.onclick=function(){ inp.value = q==='Max'? Math.floor(maxAmt) : Math.min(Math.floor(maxAmt),(parseFloat(inp.value)||0)+q); calc(); };
      quick.appendChild(b);
    });
    var go=document.createElement('button'); go.className='dg-btn gold'; go.textContent='Convert';
    go.onclick=function(){ var v=calc(); if(v<=0){ toast('Enter an amount.'); return; }
      if(v>maxAmt){ toast('Not enough to convert.'); return; }
      dgSend({type:'dg_convert', direction:dir, amount:v}); };
    card.appendChild(go);
    return card;
  }
  function renderWallet(){
    var w=wallet();
    var hd=document.createElement('div'); hd.className='dg-rates-note';
    hd.innerHTML='Spend your chat <b>Balance</b> to mint <b>Crystals</b> (1:1), then refine Crystals into <b>Gems</b> at '+(G.K.GEM_RATE||0.9)+'\u00D7. Summons and ascension are paid in Gems.';
    bodyEl.appendChild(hd);
    bodyEl.appendChild(convertCard('Balance \u2192 Crystals','$1 = \u2756 '+(G.K.CRYSTAL_RATE||1),'to_crystals', G.bal||0, (G.K.CRYSTAL_RATE||1), '$','\u2756'));
    bodyEl.appendChild(convertCard('Crystals \u2192 Gems','\u2756 1 = \u25C6 '+(G.K.GEM_RATE||0.9),'to_gems', w.crystals||0, (G.K.GEM_RATE||0.9), '\u2756','\u25C6'));
  }
  function renderBundles(){
    var w=wallet(), list=G.K.BUNDLES||[];
    var note=document.createElement('div'); note.className='dg-rates-note';
    note.innerHTML='Bundles are bought with <b>Crystals</b>. Gem bundles beat the table rate; choice bundles let you pick a die outright \u2014 no gambling.';
    bodyEl.appendChild(note);
    var grid=document.createElement('div'); grid.className='dg-bundles';
    list.forEach(function(b){
      var card=document.createElement('div'); card.className='dg-bundle'+(b.best?' best':'');
      var grant = b.grant==='select' ? ('Pick any '+capit(b.select_rarity)+' die') : ('\u25C6 '+fmt(b.gems)+' Gems');
      card.innerHTML=(b.best?'<div class="bn-best">BEST VALUE</div>':'')+
        '<div class="bn-icon">'+(b.grant==='select'?'\uD83C\uDFB4':'\u25C6')+'</div>'+
        '<div class="bn-nm">'+b.name+'</div>'+
        '<div class="bn-grant">'+grant+'</div>'+
        '<div class="bn-desc">'+b.desc+'</div>';
      var go=document.createElement('button'); go.className='dg-btn gold'; go.textContent='\u2756 '+fmt(b.cost_crystals);
      if((w.crystals||0)<b.cost_crystals){ go.disabled=true; go.title='Not enough Crystals'; }
      go.onclick=function(){ if((w.crystals||0)<b.cost_crystals){ toast('Not enough Crystals.'); return; }
        if(b.grant==='select') openBundleSelect(b); else dgSend({type:'dg_buy_bundle', bundle_id:b.id}); };
      card.appendChild(go); grid.appendChild(card);
    });
    bodyEl.appendChild(grid);
  }
  function openBundleSelect(b){
    var modal=document.createElement('div'); modal.className='dg-modal';
    modal.onclick=function(e){ if(e.target===modal) modal.remove(); };
    var sheet=document.createElement('div'); sheet.className='dg-sheet';
    var pool=G.dice.filter(function(d){ return d.rarity===b.select_rarity; });
    var grid=pool.map(function(d){
      var have=(G.state.collection||{})[d.id];
      return '<button class="dg-pick" data-id="'+d.id+'"><span class="pk-face" style="color:'+rarColor(d.rarity)+'">'+dieGlyph(d.id)+'</span>'+
        '<span class="pk-nm">'+d.name+'</span><span class="pk-rl">'+d.role+(have?' \u2022 owned':'')+'</span></button>';
    }).join('');
    sheet.innerHTML='<div class="dg-sheet-hd"><button class="dg-x">\u00D7</button><div><h2>'+b.name+'</h2>'+
      '<div class="dg-voice">Choose your '+capit(b.select_rarity)+' die \u2014 costs \u2756 '+fmt(b.cost_crystals)+'.</div></div></div>'+
      '<div class="dg-sheet-bd"><div class="dg-picks">'+grid+'</div></div>';
    modal.appendChild(sheet); root.appendChild(modal);
    sheet.querySelector('.dg-x').onclick=function(){ modal.remove(); };
    sheet.querySelectorAll('.dg-pick').forEach(function(btn){
      btn.onclick=function(){ dgSend({type:'dg_buy_bundle', bundle_id:b.id, select_id:btn.getAttribute('data-id')}); modal.remove(); };
    });
  }

  /* ================= ACHIEVEMENTS ================= */
  function achReady(check){
    var g=G.state.gacha||{}, coll=G.state.collection||{}, camp=G.state.campaign||{};
    var owned=Object.keys(coll).length;
    function anyDie(fn){ for(var id in coll){ if(fn(id,coll[id])) return true; } return false; }
    if(check==='pulls>=1') return (g.total_pulls||0)>=1;
    if(check==='owned>=10') return owned>=10;
    if(check==='owned>=all') return owned>=G.dice.length;
    if(check==='mythic>=1') return anyDie(function(id){ var d=G.byId[id]; return d&&d.rarity==='MYTHIC'; });
    if(check==='cleared_c6') return (camp.cleared||[]).indexOf('c6')>=0;
    if(check==='best_wave>=25') return (camp.best_wave||0)>=25;
    if(check==='ascended>=1') return anyDie(function(id,c){ return (c.level||0)>=1; });
    if(check==='const6>=1') return anyDie(function(id,c){ return (c.constellation||0)>=6; });
    return false;
  }
  function renderAchievements(){
    var list=G.K.ACHIEVEMENTS||[], claimed=(G.state.campaign&&G.state.campaign.achievements)||[];
    var head=document.createElement('div'); head.className='dg-rates-note';
    var got=list.filter(function(a){ return claimed.indexOf(a.id)>=0; }).length;
    head.innerHTML='Goals & rewards \u2014 <b>'+got+' / '+list.length+'</b> claimed. Hit the condition, then claim your reward here.';
    bodyEl.appendChild(head);
    var wrap=document.createElement('div'); wrap.className='dg-achs';
    list.forEach(function(a){
      var done=claimed.indexOf(a.id)>=0, ready=!done&&achReady(a.check);
      var rew=[]; if(a.gems) rew.push('\u25C6 '+a.gems); if(a.crystals) rew.push('\u2756 '+a.crystals); if(a.shards) rew.push('\u269C '+a.shards);
      var row=document.createElement('div'); row.className='dg-ach'+(done?' done':ready?' ready':' locked');
      row.innerHTML='<div class="ac-icon">'+(done?'\u2713':ready?'\u2605':'\u25CB')+'</div>'+
        '<div class="ac-body"><div class="ac-nm">'+a.name+'</div><div class="ac-desc">'+a.desc+'</div>'+
        '<div class="ac-rew">'+rew.join('  \u2022  ')+'</div></div>';
      var go=document.createElement('div'); go.className='ac-go';
      if(done){ go.innerHTML='<span class="ml-tick">Claimed</span>'; }
      else if(ready){ var b=document.createElement('button'); b.className='dg-mini gold'; b.textContent='Claim';
        b.onclick=function(){ dgSend({type:'dg_claim_achievement', ach_id:a.id}); }; go.appendChild(b); }
      else { go.innerHTML='<span class="ml-lock">In progress</span>'; }
      row.appendChild(go); wrap.appendChild(row);
    });
    bodyEl.appendChild(wrap);
  }

  /* ================= TUTORIAL ================= */
  function tutorialSeen(){ try{ return localStorage.getItem('dg_tut_seen')==='1'; }catch(e){ return true; } }
  function openTutorial(){
    var modal=document.createElement('div'); modal.className='dg-modal';
    modal.onclick=function(e){ if(e.target===modal) close(); };
    function close(){ try{ localStorage.setItem('dg_tut_seen','1'); }catch(e){} modal.remove(); }
    var secs=[
      ['\uD83D\uDCB0','Currency','Your chat <b>Balance</b> mints <b>Crystals</b> 1:1 in the Shop. Refine Crystals into <b>Gems</b> (0.9\u00D7). Summons and ascension cost Gems. <b>Universal Shards</b> come from duplicate pulls and power ascension.'],
      ['\u2684','Summoning','Spend Gems on banners. Mythic 1%, Rare 5%. Soft pity ramps from pull 70 and guarantees a Mythic by 89; every 10th pull is at least Rare. Duplicates raise a die\u2019s Constellation (C1\u2013C6); past C6 they become Shards.'],
      ['\u2694','Battle','Build a team of up to 4, then fight the Campaign or the Endless Arena. Combat is turn-based on a speed timeline. Each turn pick <b>Attack</b> (builds Energy), <b>Skill</b> (cooldown) or <b>Ultimate</b> (spends Energy). Exploit element advantages and Break enemy toughness.'],
      ['\u2728','Constellations','Constellations grant <b>utility effects</b> \u2014 starting Energy, more HP, shorter skill cooldowns, shields, even a one-time revive \u2014 never raw damage. View them on any die\u2019s detail page.'],
      ['\u269C','Ascension','Spend Universal Shards to ascend a die for flat HP/ATK/DEF growth. This is your steady power sink, separate from Constellations.'],
      ['\uD83C\uDFC6','Goals & Milestones','Claim one-time rewards from the Goals tab and from Endless Arena wave milestones (10/25/50/100). Save team Presets and follow Recommended Comps in the Team tab.']
    ];
    var body=secs.map(function(s){ return '<div class="tut-sec"><div class="tut-ic">'+s[0]+'</div><div><div class="tut-t">'+s[1]+'</div><div class="tut-d">'+s[2]+'</div></div></div>'; }).join('');
    var sheet=document.createElement('div'); sheet.className='dg-sheet';
    sheet.innerHTML='<div class="dg-sheet-hd"><button class="dg-x">\u00D7</button><div><h2>How to Play \u2014 Dice RPG</h2>'+
      '<div class="dg-voice">A quick tour of summoning, battle and progression.</div></div></div>'+
      '<div class="dg-sheet-bd">'+body+'</div>';
    var foot=document.createElement('div'); foot.style.cssText='padding:14px 18px;text-align:right';
    var ok=document.createElement('button'); ok.className='dg-btn gold'; ok.textContent='Got it';
    ok.onclick=close; foot.appendChild(ok); sheet.appendChild(foot);
    modal.appendChild(sheet); root.appendChild(modal);
    sheet.querySelector('.dg-x').onclick=close;
  }

  /* ---------- unit construction ---------- */
  function buildAlly(id){
    var die=G.byId[id], coll=(G.state.collection||{})[id]||{}, cons=coll.constellation||0;
    var s=die.stats, hp=s.hp, atk=s.atk, def=s.def, spd=s.spd;
    var lvl=coll.level||0, asc=1+lvl*(G.K.ASCENSION_STAT_PER_LEVEL||0.06);
    hp*=asc; atk*=asc; def*=asc;
    var cb=consBuffs(cons);
    if(cb.max_hp) hp*=(1+cb.max_hp);
    if(cb.def_spd){ def*=(1+cb.def_spd); spd*=(1+cb.def_spd); }
    var u={ side:'ally', id:id, name:die.name, element:die.element, role:die.role, rarity:die.rarity,
      tags:die.tags||[], params:die.params||{}, cons:cons, asc:lvl,
      max:Math.round(hp), hp:Math.round(hp), atk:atk, def:def, spd:spd,
      energy:(cb.start_energy||0), ultCost:(G.K.ULT_COST||{})[die.rarity]||80, skillCd:0,
      consSkillCdRed:(cb.skill_cd||0), canRevive:!!cb.revive, reviveVal:(cb.revive||0), revived:false,
      dmgUp:0,dmgUpT:0, critUp:0,critUpT:0, spdUp:0,spdUpT:0, defDown:0,
      shield:0, omen:0, alive:true,
      skillName:(die.skill||{}).name||'Skill', ultName:(die.ult||{}).name||'Ultimate',
      basicName:(die.basic||{}).name||'Attack' };
    if((die.params||{}).shield_pct && (die.tags||[]).indexOf('Universal')>=0 && /Shield/.test(die.role)) u.shield=Math.round(die.params.shield_pct*u.max*0.5);
    if(cb.start_shield) u.shield += Math.round(cb.start_shield*u.max);
    return u;
  }
  function consBuffs(cons){
    var o={}; (G.K.CONSTELLATION_BONUS||[]).forEach(function(c){ if(cons>=c.level) o[c.key]=c.val; }); return o;
  }
  function buildEnemy(t,tier){
    var tough=(G.K.BREAK_THRESHOLD||{})[tier]||100;
    return { side:'enemy', name:t.name, element:t.element, rarity:'RARE',
      max:t.hp, hp:t.hp, atk:t.atk, def:t.def, spd:t.spd, pow:t.pow||1.0, ai:t.ai||'basic',
      energy:0, dmgUp:0,dmgUpT:0, critUp:0,critUpT:0, spdUp:0,spdUpT:0, defDown:0,defDownT:0,
      omen:0, omenMult:(G.K.OMEN_TYPE_MULT||{})[tier]||1.1,
      toughness:tough, maxToughness:tough, broken:false, brokenTurns:0, alive:true };
  }
  function scaleEnemy(t,mult){ var e={}; for(var k in t) e[k]=t[k];
    e.hp=Math.round(t.hp*mult); e.atk=Math.round(t.atk*mult); e.def=Math.round(t.def*mult); return e; }

  function startBattle(mode,stage){
    var teamIds=(G.state.team||[]).filter(function(id){ return (G.state.collection||{})[id]; }).slice(0,G.K.TEAM_SIZE||4);
    if(!teamIds.length){ toast('Build a team first.'); G.view='team'; render(); return; }
    var B={ live:true, over:false, win:false, mode:mode, round:0,
      allies:teamIds.map(buildAlly), enemies:[], log:[], target:0, active:null, awaiting:false,
      auto:false, fortune:0, floorTurns:0, order:null, qi:0, wave:0,
      stageId:stage?stage.id:null, stageName:stage?stage.name:'Endless Arena',
      tier:stage?stage.tier:'NORMAL', stage:stage };
    G.battle=B;
    if(mode==='campaign'){ B.enemies=stage.enemies.map(function(t){ return buildEnemy(t,stage.tier); }); }
    else { spawnWave(B,1); }
    logMsg('\u2684 Battle begins \u2014 <b>'+B.stageName+'</b>!','sys');
    // start-of-battle passives: green_pip bonus energy, splinter shields already set
    B.allies.forEach(function(a){ if((a.params||{}).basic_energy) a.energy=Math.min(a.ultCost, a.energy+15); });
    G.view='battle'; render();
    scheduleStep(700);
  }
  function spawnWave(B,wave){
    B.wave=wave;
    var tier = wave%5===0?'BOSS':(wave%3===0?'ELITE':'NORMAL');
    var sc=G.K.ENDLESS_SCALE||{};
    var hpm = 1+(wave-1)*(sc.hp_per_wave||0.20);
    var atkm= 1+(wave-1)*(sc.atk_per_wave||0.12);
    var spdm= 1+(wave-1)*(sc.spd_per_wave||0.010);
    var brkm= 1+(wave-1)*(sc.break_per_wave||0.06);
    var pool=[
      {name:'Arena Pip',element:'Physical',atk:120,def:60,spd:100,hp:1500,pow:1.05,ai:'basic'},
      {name:'Arena Sharp',element:'Arcane',atk:128,def:66,spd:112,hp:1450,pow:1.1,ai:'debuff'},
      {name:'Arena Brute',element:'Fire',atk:134,def:84,spd:92,hp:1900,pow:1.15,ai:'aoe'},
      {name:'Arena Warden',element:'Ice',atk:126,def:78,spd:98,hp:1750,pow:1.1,ai:'basic'}];
    var n = tier==='BOSS'?1:(tier==='ELITE'?2:3);
    var ens=[];
    for(var i=0;i<n;i++){
      var base=pool[(wave+i)%pool.length];
      var bm = tier==='BOSS'?(sc.boss_mult||3.4):(tier==='ELITE'?(sc.elite_mult||1.8):1.0);
      var t={}; for(var k in base) t[k]=base[k];
      t.hp =Math.round(base.hp *hpm*bm);
      t.atk=Math.round(base.atk*atkm*bm);
      t.def=Math.round(base.def*hpm);
      t.spd=Math.round(base.spd*spdm);
      var en=buildEnemy(t, tier);
      en.maxToughness=en.toughness=Math.round(en.maxToughness*brkm);
      if(tier==='BOSS') en.name='Arena Colossus';
      ens.push(en);
    }
    B.enemies=ens; B.tier=tier; B.stageName='Endless Arena \u2014 Wave '+wave;
    B.target=0;
  }

  /* ---------- combat math ---------- */
  function rollDie(r){ return 1+Math.floor(Math.random()*((G.K.RARITY_DIE||{})[r]||6)); }
  function allyRoll(u){
    var B=G.battle, max=(G.K.RARITY_DIE||{})[u.rarity]||6, r=rollDie(u.rarity);
    if(B.fortune>0){ B.fortune--; var r2=rollDie(u.rarity); if(r2>r) r=r2; }
    if(B.floorTurns>0){ var fl=Math.ceil(max*0.30); if(r<fl) r=fl; }
    return r;
  }
  function elemMult(a,d){ if(ELEM_ADV[a]===d) return 1.3; if(ELEM_ADV[d]===a) return 0.85; return 1.0; }
  function aliveEnemies(){ return G.battle.enemies.filter(function(e){ return e.alive; }); }
  function aliveAllies(){ return G.battle.allies.filter(function(a){ return a.alive; }); }
  function curTarget(){ var en=G.battle.enemies; var t=en[G.battle.target];
    if(t&&t.alive) return t; var a=aliveEnemies(); return a.length?a[0]:null; }
  function applyDamage(tgt,dmg){
    if(tgt.shield>0){ var ab=Math.min(tgt.shield,dmg); tgt.shield-=ab; dmg-=ab; }
    tgt.hp-=dmg; tgt._flash=true;
    if(tgt.hp<=0){
      if(tgt.side==='ally' && tgt.canRevive && !tgt.revived){
        tgt.revived=true; tgt.alive=true; tgt.hp=Math.max(1,Math.round(tgt.max*(tgt.reviveVal||0.3)));
        logMsg('\u2728 <b>'+tgt.name+'</b> defies fate \u2014 revived at '+Math.round((tgt.reviveVal||0.3)*100)+'% HP!','heal');
      } else { tgt.hp=0; tgt.alive=false; }
    }
    if(tgt.side==='ally' && tgt.alive) addEnergy(tgt,6);
  }
  function addEnergy(u,a){ u.energy=Math.min(u.ultCost,(u.energy||0)+a); }
  function teamEnergy(a){ aliveAllies().forEach(function(u){ addEnergy(u,a); }); }
  function applyOmen(tgt,n){ if(!tgt||!tgt.alive) return; tgt.omen=Math.min((G.K.OMEN_SOFT_CAP||9999),(tgt.omen||0)+n); }
  function detonateOmen(tgt){
    if(!tgt||!tgt.alive||tgt.omen<=0) return 0;
    var dmg=Math.round(tgt.omen*22*(tgt.omenMult||1.1));
    applyDamage(tgt,dmg);
    logMsg('Omen detonates on <b>'+tgt.name+'</b> for '+fmt(dmg)+' ('+tgt.omen+' stacks).','omen');
    tgt.omen=0; return dmg;
  }
  function addBreak(tgt,amt){
    if(!tgt||!tgt.alive||tgt.broken) return;
    tgt.toughness-=amt;
    if(tgt.toughness<=0){ tgt.toughness=0; tgt.broken=true; tgt.brokenTurns=1;
      logMsg('<b>'+tgt.name+'</b> is BROKEN!','brk'); }
  }
  function computeHit(src,tgt,mult,opts){
    opts=opts||{};
    if(!tgt||!tgt.alive) return null;
    var roll = src.side==='ally'? allyRoll(src) : rollDie('RARE');
    var base = src.atk*mult*roll*SCALE;
    base *= elemMult(src.element,tgt.element);
    base *= (1+(src.dmgUp||0));
    if(opts.mult) base*=opts.mult;
    var cc=(G.K.CRIT_BASE||0.08)+(src.critUp||0), crit=opts.crit||Math.random()<cc;
    if(crit) base*=(G.K.CRIT_MULT||1.5);
    var tdef=tgt.def*(1-(tgt.defDown||0)); if(tdef<0) tdef=0;
    base*=220/(220+tdef);
    if(tgt.broken) base*=(G.K.BROKEN_DMG_MULT||1.3);
    var dmg=Math.max(1,Math.round(base));
    applyDamage(tgt,dmg);
    return {dmg:dmg,crit:crit,roll:roll};
  }
  function primaryTag(u){ var t=u.tags||[];
    if(t.indexOf('Omen')>=0) return 'Omen';
    if(t.indexOf('Break')>=0) return 'Break';
    if(t.indexOf('Fortune')>=0) return 'Fortune';
    return 'Universal'; }

  /* ---------- ally abilities (interpreter) ---------- */
  var DM={BASIC:0.015,SKILL:0.045,ULT:0.18};
  function K_DM(){ return G.K.DMG_MULT||DM; }
  function useBasic(u){
    var t=curTarget(); if(!t) return;
    var p=u.params||{}, dm=K_DM();
    var r=computeHit(u,t,dm.BASIC);
    sfx(r&&r.crit?'crit':'hit');
    logMsg('<b>'+u.name+'</b> uses '+u.basicName+(r&&r.crit?' \u2014 <span style="color:#ffce5a">CRIT!</span>':'')+' for '+fmt(r?r.dmg:0)+'.','dmg');
    if(p.double_chance && Math.random()<p.double_chance){ var r2=computeHit(u,t,dm.BASIC*0.6);
      if(r2) logMsg('\u21B3 strikes again for '+fmt(r2.dmg)+'.','dmg'); }
    addEnergy(u,22);
    if(p.basic_energy) teamEnergy(p.basic_energy);
    if(p.basic_omen) applyOmen(t,p.basic_omen);
    if((u.tags||[]).indexOf('Break')>=0) addBreak(t,8);
    if(primaryTag(u)==='Omen' && p.basic_omen) {}
  }
  function useSkill(u){
    var t=curTarget(); if(!t) return;
    var p=u.params||{}, dm=K_DM(), c3=false, mag=1, tag=primaryTag(u), turns=(p.skill_turns||2);
    sfx('hit');
    addEnergy(u,12); u.skillCd=Math.max(0, 2-(u.consSkillCdRed||0));
    // riders
    if(p.skill_omen) applyOmen(t,Math.round(p.skill_omen*mag));
    if(p.skill_energy) teamEnergy(Math.round(p.skill_energy*mag));
    if(p.floor_pct){ G.battle.floorTurns=Math.max(G.battle.floorTurns,turns); }
    if(p.team_fortune) G.battle.fortune+=p.team_fortune;
    if(p.crit_up) buffTeam('critUp',p.crit_up*mag,turns);
    if(p.dmg_up) buffTeam('dmgUp',p.dmg_up*mag,turns);
    if(p.spd_up) buffTeam('spdUp',p.spd_up*mag,turns);
    if(p.def_down){ t.defDown=Math.max(t.defDown||0,p.def_down*mag); t.defDownT=turns; }
    if(p.shield_pct){ var sh=Math.round(p.shield_pct*u.max*mag); aliveAllies().forEach(function(a){ a.shield=(a.shield||0)+sh; }); }
    // damage
    var msg='<b>'+u.name+'</b> uses '+u.skillName;
    if(tag==='Break'){ addBreak(t,Math.round(26*mag));
      var rb=computeHit(u,t,dm.SKILL,{skillC3:c3, mult:t.broken?(1+(p.broken_bonus||0)):1});
      msg+=' for '+fmt(rb?rb.dmg:0)+'.'; }
    else if(p.skill_hits){ var tot=0; for(var i=0;i<p.skill_hits;i++){ var rh=computeHit(u,t,dm.SKILL*0.55,{skillC3:c3}); if(rh) tot+=rh.dmg; }
      msg+=' \u2014 '+p.skill_hits+' hits for '+fmt(tot)+'.'; }
    else { var rs=computeHit(u,t,dm.SKILL,{skillC3:c3}); msg+=' for '+fmt(rs?rs.dmg:0)+'.'; }
    logMsg(msg,'dmg');
    if(tag==='Omen') detonateOmen(t);
    if(p.skill_energy||p.shield_pct||p.crit_up||p.dmg_up||p.spd_up||p.team_fortune||p.floor_pct)
      logMsg('\u21B3 '+u.name+' empowers the team.','sys');
  }
  function useUlt(u){
    var t=curTarget(); var p=u.params||{}, dm=K_DM(), c5=false, mag=1.15, tag=primaryTag(u);
    u.energy=0;
    sfx('ult');
    logMsg('\u2728 <b>'+u.name+'</b> unleashes '+u.ultName+'!','sys');
    if(p.ult_energy) teamEnergy(p.ult_energy);
    if(tag==='Omen'){
      var trig=p.ult_omen_triggers||1, total=0;
      aliveEnemies().forEach(function(e){
        if(p.ult_bonus_omen||p.ult_omen) applyOmen(e,(p.ult_bonus_omen||p.ult_omen||0));
        var r=computeHit(u,e,dm.ULT,{ultC5:c5}); if(r) total+=r.dmg;
        for(var k=0;k<trig;k++) detonateOmen(e);
      });
      logMsg('\u21B3 AoE Omen burst hits all foes for '+fmt(total)+'+.','omen');
    } else if(tag==='Break' && t){
      var miss=t.maxToughness?(t.maxToughness-t.toughness)/t.maxToughness:0;
      var r=computeHit(u,t,dm.ULT,{ultC5:c5, mult:1+miss*0.8});
      logMsg('\u21B3 Collapsing strike for '+fmt(r?r.dmg:0)+'.','dmg');
    } else {
      // support / DPS: buffs + damage
      if(p.dmg_up) buffTeam('dmgUp',p.dmg_up*1.3,2);
      if(p.crit_up){ buffTeam('critUp',0.5,1); }
      if(p.spd_up) buffTeam('spdUp',p.spd_up*1.3,2);
      if(p.shield_pct){ var sh=Math.round(p.shield_pct*u.max*1.5); aliveAllies().forEach(function(a){ a.shield=(a.shield||0)+sh; }); logMsg('\u21B3 Team shielded for '+fmt(sh)+'.','heal'); }
      if(p.team_fortune) G.battle.fortune+=p.team_fortune+1;
      var multi=(u.role||'').indexOf('Multi')>=0 || (u.tags||[]).indexOf('Break')>=0;
      if(multi){ var total2=0; aliveEnemies().forEach(function(e){ var r=computeHit(u,e,dm.ULT*0.62,{ultC5:c5}); if(r) total2+=r.dmg; });
        logMsg('\u21B3 sweeps all foes for '+fmt(total2)+'.','dmg'); }
      else if(t){ var r3=computeHit(u,t,dm.ULT,{ultC5:c5}); logMsg('\u21B3 hits '+t.name+' for '+fmt(r3?r3.dmg:0)+'.','dmg'); }
    }
  }
  function buffTeam(field,val,turns){ aliveAllies().forEach(function(a){ a[field]=Math.max(a[field]||0,val); a[field+'T']=Math.max(a[field+'T']||0,turns); }); }

  /* ---------- enemy AI ---------- */
  function enemyTurn(e){
    var allies=aliveAllies(); if(!allies.length) return;
    e.energy=(e.energy||0)+34;
    var special = e.energy>=100 && e.ai!=='basic';
    if(special){ e.energy=0;
      if(e.ai==='aoe'){ var tot=0; allies.forEach(function(a){ var r=enemyHit(e,a,(e.pow||1)*0.62); tot+=r; });
        logMsg('<b>'+e.name+'</b> sweeps the team for '+fmt(tot)+'.','dmg'); return; }
      if(e.ai==='debuff'){ var tg=lowest(allies,'def'); enemyHit(e,tg,e.pow||1);
        var v=0.25; tg.defDown=Math.max(tg.defDown||0,v); tg.defDownT=2;
        logMsg('<b>'+e.name+'</b> exposes <b>'+tg.name+'</b> (DEF down).','dmg'); return; }
      if(e.ai==='heal'){ var hurt=lowestEnemy(); if(hurt){ var h=Math.round(hurt.max*0.18); hurt.hp=Math.min(hurt.max,hurt.hp+h);
        logMsg('<b>'+e.name+'</b> heals <b>'+hurt.name+'</b> for '+fmt(h)+'.','heal'); } return; }
      if(e.ai==='boss'){ var tot2=0; allies.forEach(function(a){ var r=enemyHit(e,a,(e.pow||1)*0.7); tot2+=r; });
        var foc=lowest(allies,'hp'); if(foc&&foc.alive){ foc.dmgUp=Math.min(foc.dmgUp||0,0); }
        logMsg('<b>'+e.name+'</b> tilts the table \u2014 AoE for '+fmt(tot2)+'.','dmg'); return; }
    }
    var tgt = Math.random()<0.5? lowest(allies,'hp') : allies[(Math.random()*allies.length)|0];
    var dmg=enemyHit(e,tgt,e.pow||1);
    logMsg('<b>'+e.name+'</b> attacks <b>'+tgt.name+'</b> for '+fmt(dmg)+'.','dmg');
  }
  function enemyHit(e,tgt,pow){
    var base=e.atk*pow*(0.9+Math.random()*0.3)*1.0;
    base*=elemMult(e.element,tgt.element);
    var tdef=tgt.def*(1-(tgt.defDown||0)); if(tdef<0) tdef=0;
    base*=220/(220+tdef);
    if(Math.random()<0.08) base*=1.4;
    var dmg=Math.max(1,Math.round(base*1.7));
    applyDamage(tgt,dmg);
    return dmg;
  }
  function lowest(arr,f){ var b=arr[0]; arr.forEach(function(x){ if(x[f]<b[f]) b=x; }); return b; }
  function lowestEnemy(){ var a=aliveEnemies(); if(!a.length) return null; var b=a[0];
    a.forEach(function(x){ if(x.hp/x.max < b.hp/b.max) b=x; }); return b; }

  /* ---------- turn loop ---------- */
  function tickBuffs(u){
    ['dmgUp','critUp','spdUp'].forEach(function(f){ if(u[f+'T']>0){ u[f+'T']--; if(u[f+'T']<=0) u[f]=0; } });
    if(u.side==='enemy' && u.defDownT>0){ u.defDownT--; if(u.defDownT<=0) u.defDown=0; }
  }
  function effSpd(u){ return u.spd*(1+(u.spdUp||0)); }
  function startRound(){ var B=G.battle; B.round++;
    if(B.floorTurns>0) B.floorTurns--;
    B.order=B.allies.concat(B.enemies).filter(function(u){return u.alive;}).sort(function(a,b){return effSpd(b)-effSpd(a);});
    B.qi=0; }
  function sd(ms){ return Math.max(50, (ms||0)/(G.speed||1)); }
  function scheduleStep(ms){ G.timers.push(setTimeout(step, sd(ms||520))); }
  function step(){
    var B=G.battle; if(!B||B.over) return;
    if(!B.order || B.qi>=B.order.length) startRound();
    var u=B.order[B.qi++];
    if(!u || !u.alive){ return scheduleStep(120); }
    tickBuffs(u);
    if(u.side==='enemy' && u.broken){ u.brokenTurns--;
      if(u.brokenTurns<=0){ u.broken=false; u.toughness=u.maxToughness; logMsg('<b>'+u.name+'</b> recovers from Break.','brk'); }
      else logMsg('<b>'+u.name+'</b> is Broken and loses its turn.','brk');
      B.active=u; B.phase='Broken'; if(G.view==='battle') renderBattle(); return scheduleStep(700); }
    B.active=u;
    if(u.side==='ally'){
      if(u.skillCd>0) u.skillCd--;
      B.awaiting=true; B.phase='Your move'; if(G.view==='battle') renderBattle();
      if(B.auto) G.timers.push(setTimeout(function(){ autoAct(u); },sd(620)));
    } else {
      B.awaiting=false; B.phase='Enemy turn'; if(G.view==='battle') renderBattle();
      G.timers.push(setTimeout(function(){ if(G.battle!==B||B.over) return; enemyTurn(u); afterAction(); },sd(680)));
    }
  }
  function afterAction(){ var B=G.battle; if(!B) return;
    if(checkEnd()) return;
    B.phase='Resolving'; if(G.view==='battle') renderBattle();
    scheduleStep(560); }
  function autoAct(u){ var B=G.battle; if(!B||B.over||B.active!==u) return;
    if(u.energy>=u.ultCost) useUlt(u);
    else if(u.skillCd<=0 && Math.random()<0.7) useSkill(u);
    else useBasic(u);
    B.awaiting=false; afterAction(); }
  function playerAct(kind){
    var B=G.battle; if(!B||B.over||!B.awaiting||!B.active||B.active.side!=='ally') return;
    var u=B.active;
    if(kind==='skill' && u.skillCd>0) return;
    if(kind==='ult' && u.energy<u.ultCost) return;
    if(kind==='ult') useUlt(u); else if(kind==='skill') useSkill(u); else useBasic(u);
    B.awaiting=false; afterAction();
  }
  function checkEnd(){
    var B=G.battle;
    if(!aliveEnemies().length){
      if(B.mode==='endless'){ // next wave
        var nw=B.wave+1; updateBestWave(B.wave);
        logMsg('Wave '+B.wave+' cleared! Wave '+nw+' approaches\u2026','sys');
        spawnWave(B,nw); B.order=null;
        if(G.view==='battle') renderBattle();
        scheduleStep(900); return true;
      }
      B.over=true; B.win=true; sfx('win'); onWin(); return true;
    }
    if(!aliveAllies().length){ B.over=true; B.win=false; sfx('lose');
      if(B.mode==='endless') updateBestWave(B.wave-1);
      logMsg('Your team has fallen\u2026','sys'); if(G.view==='battle') renderBattle(); return true; }
    return false;
  }
  function updateBestWave(w){ if(!G.state.campaign) G.state.campaign={cleared:[],best_wave:0};
    if(w>(G.state.campaign.best_wave||0)){ G.state.campaign.best_wave=w; dgSend({type:'dg_set_best_wave', wave:w}); } }
  function onWin(){
    var B=G.battle; logMsg('Victory! <b>'+B.stageName+'</b> cleared.','sys');
    var cleared=clearedList();
    if(B.mode==='campaign' && cleared.indexOf(B.stageId)<0){
      B.rewardPending=true; dgSend({type:'dg_claim_reward', stage:B.stageId});
    }
    if(G.view==='battle') renderBattle();
  }
  window._dgOnReward=function(d){
    var B=G.battle;
    if(d && d.ok){
      if(typeof d.balance==='number'){ G.bal=d.balance; updateBal(); }
      if(d.state) G.state=d.state;
      if(B){ B.rewardPending=false; B.rewardGot=d.reward||0; if(G.view==='battle') renderBattle(); }
      sfx('win'); toast('First clear! +'+fmt(d.reward||0)+' Gems.');
    } else if(B){ B.rewardPending=false; if(G.view==='battle') renderBattle(); }
  };
  function fleeBattle(){ if(G.battle) G.battle.over=true; G.battle=null; render(); }
  function nextStage(){
    var B=G.battle; if(!B||!B.stageId){ G.battle=null; G.hubTab='campaign'; render(); return; }
    var idx=campIndex(B.stageId), nx=CAMPAIGN[idx+1];
    G.battle=null;
    if(nx) startBattle('campaign',nx); else { G.hubTab='campaign'; render(); }
  }

  /* ---------- battle log ---------- */
  function logMsg(html,cls){ var B=G.battle; if(!B) return;
    B.log.push({h:html,c:cls||''}); if(B.log.length>90) B.log.shift();
    if(G.view==='battle'){ var box=root.querySelector('.dg-log'); if(box){ appendLog(box,B.log[B.log.length-1]); box.scrollTop=box.scrollHeight; } }
  }
  function appendLog(box,e){ var d=document.createElement('div'); d.className='dg-log-line '+(e.c||''); d.innerHTML=e.h; box.appendChild(d); }

  /* ---------- turn-order timeline ---------- */
  function turnTimeline(){
    var B=G.battle;
    var wrap=document.createElement('div'); wrap.className='dg-timeline';
    var lbl=document.createElement('span'); lbl.className='tl-lbl'; lbl.textContent='Turn order'; wrap.appendChild(lbl);
    var strip=document.createElement('div'); strip.className='tl-strip';
    var ord = B.order && B.order.length ? B.order.slice(B.qi-1<0?0:B.qi-1) : B.allies.concat(B.enemies).filter(function(u){return u.alive;}).sort(function(a,b){return effSpd(b)-effSpd(a);});
    ord = ord.filter(function(u){ return u&&u.alive; }).slice(0,10);
    ord.forEach(function(u,idx){
      var pip=document.createElement('div');
      pip.className='tl-pip '+(u.side)+(B.active===u?' now':'');
      var g = u.side==='ally'? dieGlyph(u.id) : tierGlyph(B.tier);
      pip.innerHTML='<span class="tl-face" style="color:'+(u.side==='ally'?rarColor(u.rarity):'#ff8a8a')+'">'+g+'</span>';
      pip.title=u.name+(B.active===u?' (acting now)':'')+' \u2022 SPD '+Math.round(effSpd(u));
      strip.appendChild(pip);
    });
    wrap.appendChild(strip);
    return wrap;
  }

  /* ---------- battle render ---------- */
  function renderBattle(){
    if(G.view!=='battle') return;
    var B=G.battle; if(!B){ bodyEl.innerHTML=''; renderBattleHub(); return; }
    bodyEl.innerHTML='';
    var arena=document.createElement('div'); arena.className='dg-arena';
    var main=document.createElement('div'); main.className='dg-arena-main';
    // top bar
    var top=document.createElement('div'); top.className='dg-battle-top';
    top.innerHTML='<div><div class="bt-nm">'+B.stageName+'</div><div class="bt-rd">Round '+Math.max(1,B.round)+
      ' \u2022 '+B.tier+(B.phase?(' \u2022 <span class="bt-phase">'+B.phase+'</span>'):'')+'</div></div>';
    var acts=document.createElement('div'); acts.className='bt-actions';
    var speeds=G.K.SPEED_OPTIONS||[0.75,1,1.5];
    var spd=document.createElement('button'); spd.className='dg-mini-btn'; spd.textContent=(G.speed||1)+'\u00D7'; spd.title='Battle speed';
    spd.onclick=function(){ var i=speeds.indexOf(G.speed||1); G.speed=speeds[(i+1)%speeds.length]||1;
      try{ localStorage.setItem('dg_speed',String(G.speed)); }catch(e){} renderBattle(); };
    var autoBtn=document.createElement('button'); autoBtn.className='dg-mini-btn'+(B.auto?' on':''); autoBtn.textContent='Auto';
    autoBtn.onclick=function(){ B.auto=!B.auto; renderBattle(); if(B.auto && B.awaiting && B.active) G.timers.push(setTimeout(function(){ autoAct(B.active); },sd(300))); };
    var flee=document.createElement('button'); flee.className='dg-mini-btn'; flee.textContent='Flee';
    flee.onclick=fleeBattle; acts.appendChild(spd); acts.appendChild(autoBtn); acts.appendChild(flee); top.appendChild(acts);
    main.appendChild(top);
    main.appendChild(turnTimeline());
    // enemies
    var eg=document.createElement('div'); eg.className='dg-side-group';
    var el=document.createElement('div'); el.className='dg-side-label'; el.textContent='Enemies'; eg.appendChild(el);
    var eu=document.createElement('div'); eu.className='dg-units enemies';
    B.enemies.forEach(function(e,i){ eu.appendChild(unitCard(e,'enemy',i)); });
    eg.appendChild(eu); main.appendChild(eg);
    // allies
    var ag=document.createElement('div'); ag.className='dg-side-group';
    var al=document.createElement('div'); al.className='dg-side-label'; al.textContent='Your Team'; ag.appendChild(al);
    var au=document.createElement('div'); au.className='dg-units';
    B.allies.forEach(function(a,i){ au.appendChild(unitCard(a,'ally',i)); });
    ag.appendChild(au); main.appendChild(ag);
    // action panel
    main.appendChild(actionPanel());
    arena.appendChild(main);
    // log sidebar
    var side=document.createElement('div'); side.className='dg-arena-side';
    var h=document.createElement('h4'); h.textContent='Battle Log'; side.appendChild(h);
    var log=document.createElement('div'); log.className='dg-log';
    B.log.forEach(function(e){ appendLog(log,e); }); side.appendChild(log);
    arena.appendChild(side);
    bodyEl.appendChild(arena);
    G.timers.push(setTimeout(function(){ var lb=root.querySelector('.dg-log'); if(lb) lb.scrollTop=lb.scrollHeight; },10));
    if(B.over) bodyEl.appendChild(resultOverlay());
  }
  function unitCard(u,side,i){
    var B=G.battle;
    var c=document.createElement('div');
    c.className='dg-unit '+side+(u.alive?'':' dead')+(B.active===u?' active':'')+
      (side==='enemy'&&B.target===i&&u.alive?' target':'')+(u._flash?' hit':'');
    u._flash=false;
    var glyph = side==='ally'? dieGlyph(u.id) : tierGlyph(B.tier);
    var sub = side==='ally'? (capit(u.rarity)+(u.cons>0?' \u2022 C'+u.cons:'')) : u.role||'Foe';
    c.innerHTML='<div class="dg-unit-hd"><span class="dg-unit-glyph" style="color:'+(side==='ally'?rarColor(u.rarity):'#ff8a8a')+'">'+glyph+'</span>'+
      '<div style="min-width:0;flex:1"><div class="dg-unit-nm">'+u.name+'</div><div class="dg-unit-sub">'+sub+'</div></div>'+
      '<span class="dg-unit-el" style="color:'+elemColor(u.element)+'">'+u.element+'</span></div>'+
      '<div class="dg-hpbar"><i style="width:'+(u.hp/u.max*100)+'%"></i></div>'+
      '<div class="dg-hptext"><span>'+fmt(u.hp)+' / '+fmt(u.max)+'</span>'+(u.shield>0?'<span style="color:#9be4ff">\u26E8 '+fmt(u.shield)+'</span>':'')+'</div>';
    if(side==='ally'){
      var eb=document.createElement('div'); eb.className='dg-enbar';
      eb.innerHTML='<i style="width:'+Math.min(100,u.energy/u.ultCost*100)+'%"></i>'; c.appendChild(eb);
    } else if(!u.broken){
      var tb=document.createElement('div'); tb.className='dg-tough';
      tb.innerHTML='<i style="width:'+(u.maxToughness?u.toughness/u.maxToughness*100:0)+'%"></i>'; c.appendChild(tb);
    }
    // chips
    var chips=[];
    if(side==='enemy'){ if(u.broken) chips.push('<span class="dg-chip-s brk">BROKEN</span>');
      if(u.omen>0) chips.push('<span class="dg-chip-s omen">Omen '+u.omen+'</span>');
      if(u.defDown>0) chips.push('<span class="dg-chip-s deb">DEF\u2193</span>'); }
    else { if(u.dmgUp>0) chips.push('<span class="dg-chip-s buff">DMG\u2191</span>');
      if(u.critUp>0) chips.push('<span class="dg-chip-s buff">CRIT\u2191</span>');
      if(u.spdUp>0) chips.push('<span class="dg-chip-s buff">SPD\u2191</span>');
      if(u.energy>=u.ultCost) chips.push('<span class="dg-chip-s fort">ULT READY</span>'); }
    if(chips.length){ var ch=document.createElement('div'); ch.className='dg-chips'; ch.innerHTML=chips.join(''); c.appendChild(ch); }
    if(side==='enemy') c.onclick=function(){ if(u.alive){ B.target=i; renderBattle(); } };
    return c;
  }
  function actionPanel(){
    var B=G.battle, p=document.createElement('div'); p.className='dg-actpanel';
    if(B.over){ p.innerHTML='<div class="ap-who">Battle over.</div>'; return p; }
    var u=B.active;
    if(!u || u.side!=='ally' || !B.awaiting){
      p.innerHTML='<div class="ap-who">'+(u?('<b>'+u.name+'</b> is acting\u2026'):'Preparing\u2026')+'</div>';
      return p;
    }
    var who=document.createElement('div'); who.className='ap-who';
    who.innerHTML=u.name+'<small>'+capit(u.rarity)+' \u2022 Energy '+Math.floor(u.energy)+'/'+u.ultCost+'</small>';
    p.appendChild(who);
    var bw=document.createElement('div'); bw.className='dg-act-btns';
    var bBasic=document.createElement('button'); bBasic.className='dg-act'; bBasic.innerHTML=u.basicName+'<small>Basic</small>';
    bBasic.onclick=function(){ playerAct('basic'); };
    var bSkill=document.createElement('button'); bSkill.className='dg-act skill'; bSkill.innerHTML=u.skillName+'<small>'+(u.skillCd>0?'Cooldown':'Skill')+'</small>';
    bSkill.disabled=u.skillCd>0; bSkill.onclick=function(){ playerAct('skill'); };
    var bUlt=document.createElement('button'); bUlt.className='dg-act ult'; bUlt.innerHTML=u.ultName+'<small>'+(u.energy>=u.ultCost?'Ultimate':'Charging '+Math.floor(u.energy)+'/'+u.ultCost)+'</small>';
    bUlt.disabled=u.energy<u.ultCost; bUlt.onclick=function(){ playerAct('ult'); };
    bw.appendChild(bBasic); bw.appendChild(bSkill); bw.appendChild(bUlt); p.appendChild(bw);
    return p;
  }
  function resultOverlay(){
    var B=G.battle, o=document.createElement('div'); o.className='dg-result'+(B.win?' win':'');
    var h=document.createElement('h1'); h.textContent=B.win?'VICTORY':'DEFEAT'; o.appendChild(h);
    if(B.win && B.mode==='campaign'){
      var r=document.createElement('div'); r.className='rs-reward';
      r.textContent = B.rewardPending? 'Claiming first-clear reward\u2026' : (B.rewardGot? ('First clear reward: +'+fmt(B.rewardGot)+' balance!') : 'Stage already cleared \u2014 no reward.');
      o.appendChild(r);
    }
    if(B.win && B.mode==='endless'){
      var r2=document.createElement('div'); r2.className='rs-reward'; r2.textContent='Reached Wave '+B.wave+'.'; o.appendChild(r2);
    }
    var btns=document.createElement('div'); btns.style.cssText='display:flex;gap:10px;flex-wrap:wrap;justify-content:center';
    if(B.win && B.mode==='campaign' && campIndex(B.stageId)<CAMPAIGN.length-1){
      var nb=document.createElement('button'); nb.className='dg-btn gold'; nb.textContent='Next Stage'; nb.onclick=nextStage; btns.appendChild(nb);
    }
    if(!B.win){ var rb=document.createElement('button'); rb.className='dg-btn gold'; rb.textContent='Retry';
      rb.onclick=function(){ var st=B.stage, md=B.mode; G.battle=null; if(md==='endless') startBattle('endless',null); else startBattle('campaign',st); }; btns.appendChild(rb); }
    var back=document.createElement('button'); back.className='dg-btn ghost'; back.textContent='Back to Hub';
    back.onclick=function(){ G.battle=null; render(); }; btns.appendChild(back);
    o.appendChild(btns);
    return o;
  }

  /* ---------- placeholder ---------- */
  function renderSoon(title,glyph,msg){
    var d=document.createElement('div'); d.className='dg-soon';
    d.innerHTML='<div class="big">'+glyph+'</div><h2 style="margin:0">'+title+'</h2><p>'+msg+'</p>';
    bodyEl.appendChild(d);
  }

  /* ---------- cleanup ---------- */
  window._gameCleanup=function(){
    G.timers.forEach(function(t){ clearTimeout(t); clearInterval(t); });
    G.timers=[];
    window._diceMessageHandler=null; window._dgOnPull=null; window._dgOnReward=null;
    window._gameCleanup=null;
  };
}
"""
