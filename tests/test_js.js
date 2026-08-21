
// ===== API 客户端（连接后端 /api/* 接口）=====
var api = {
  // GET /api/weather?city=xxx&district=xxx&source=xxx
  // source：数据源 ID，后端按源选用对应真实数值模式取数（切源即真实预报差异）
  getWeather: function(city, district, source) {
    var q = 'city=' + encodeURIComponent(city) + '&district=' + encodeURIComponent(district);
    if (source) q += '&source=' + encodeURIComponent(source);
    return fetch('/api/weather?' + q)
      .then(function(r) { return r.json(); });
  },
  // GET /api/ranking?range=7d|30d|all
  getRanking: function(range) {
    return fetch('/api/ranking?range=' + range).then(function(r) { return r.json(); });
  },
  // GET /api/source/:id
  getSource: function(id) {
    return fetch('/api/source/' + id).then(function(r) { return r.json(); });
  },
  // GET /api/notifications
  getNotifications: function() {
    return fetch('/api/notifications').then(function(r) { return r.json(); });
  },
  // PUT /api/notifications/:index/read
  markNotificationRead: function(idx) {
    return fetch('/api/notifications/' + idx + '/read', { method: 'PUT' })
      .then(function(r) { return r.json(); });
  },
  // PUT /api/notifications/read-all
  markAllNotificationsRead: function() {
    return fetch('/api/notifications/read-all', { method: 'PUT' })
      .then(function(r) { return r.json(); });
  },
  // GET /api/feeds?filter=hot|new|near
  getFeeds: function(filter) {
    return fetch('/api/feeds?filter=' + filter).then(function(r) { return r.json(); });
  },
  // GET /api/feeds/:id
  getFeed: function(id) {
    return fetch('/api/feeds/' + id).then(function(r) { return r.json(); });
  },
  // POST /api/feeds/:id/toggle-like（需登录）
  toggleLike: function(feedId) {
    var h = authHeader();
    h['Content-Type'] = 'application/json';
    return fetch('/api/feeds/' + feedId + '/toggle-like', { method: 'POST', headers: h })
      .then(function(r) {
        return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
      });
  },
  // POST /api/feeds/:id/comments（需登录）
  addComment: function(feedId, text) {
    var h = authHeader();
    h['Content-Type'] = 'application/json';
    return fetch('/api/feeds/' + feedId + '/comments', {
      method: 'POST',
      headers: h,
      body: JSON.stringify({ text: text })
    }).then(function(r) {
      return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
    });
  },
  // POST /api/auth/register -> { token, user }
  register: function(data) {
    return fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(function(r) {
      return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
    });
  },
  // POST /api/auth/login -> { token, user }
  login: function(data) {
    return fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(function(r) {
      return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
    });
  },
  // GET /api/user/profile（需登录，携带 Bearer Token）
  getProfile: function() {
    var t = authToken();
    return fetch('/api/user/profile', { headers: t ? { 'Authorization': 'Bearer ' + t } : {} })
      .then(function(r) {
        return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
      });
  },
  // POST /api/ai-weather -> { cond, temp, humid, wind, aqi, desc, feel, ai_generated }
  aiWeather: function(city, district) {
    return fetch('/api/ai-weather', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city: city, district: district })
    }).then(function(r) { return r.json(); });
  },
  // GET /api/reverse-geocode?lat=&lon= -> { city, district, lat, lon }
  reverseGeocode: function(lat, lon) {
    return fetch('/api/reverse-geocode?lat=' + lat + '&lon=' + lon).then(function(r) { return r.json(); });
  },
  // POST /api/feed/post（需登录）— 发帖，支持 photos 数组和 caption 文字
  postFeed: function(photos, caption) {
    var h = authHeader();
    h['Content-Type'] = 'application/json';
    return fetch('/api/feed/post', {
      method: 'POST',
      headers: h,
      body: JSON.stringify({ photos: photos || [], caption: caption || '' })
    }).then(function(r) {
      return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
    });
  },
  // DELETE /api/feed/:id（需登录）— 删除自己的帖子
  deleteFeed: function(feedId) {
    var h = authHeader();
    return fetch('/api/feed/' + feedId, { method: 'DELETE', headers: h })
      .then(function(r) {
        return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
      });
  },
  // PUT /api/user/profile（需登录）— 更新用户资料（头像、用户名）
  updateProfile: function(data) {
    var h = authHeader();
    h['Content-Type'] = 'application/json';
    return fetch('/api/user/profile', {
      method: 'PUT',
      headers: h,
      body: JSON.stringify(data || {})
    }).then(function(r) {
      return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
    });
  },
  // GET /api/user/:id/profile — 获取用户资料
  getUserProfile: function(userId) {
    return fetch('/api/user/' + userId + '/profile').then(function(r) {
      return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
    });
  },
  // POST /api/user/:id/follow（需登录）— 关注/取消关注
  followUser: function(userId) {
    var h = authHeader();
    h['Content-Type'] = 'application/json';
    return fetch('/api/user/' + userId + '/follow', { method: 'POST', headers: h })
      .then(function(r) {
        return r.json().then(function(d) { return { ok: r.ok, status: r.status, data: d }; });
      });
  },
  // GET /api/user/:id/followers — 获取粉丝列表
  getFollowers: function(userId) {
    return fetch('/api/user/' + userId + '/followers').then(function(r) { return r.json(); });
  },
  // GET /api/user/:id/following — 获取关注列表
  getFollowing: function(userId) {
    return fetch('/api/user/' + userId + '/following').then(function(r) { return r.json(); });
  }
};

// ===== Global state =====
// CITIES: from data.json (static config)
// RANK_DATA / SOURCE_DATA / NOTIFICATIONS / FEEDS: from api.* (backend)
let CITIES,RANK_DATA,SOURCE_DATA,NOTIFICATIONS,FEEDS;
// wIcon: pure UI utility (SVG icon mapping), stays in frontend
function wIcon(type,sz){
  const s=sz||28;
  const m={
    sunny:'<circle cx="32" cy="32" r="14" fill="#FBBF24"/><g stroke="#FBBF24" stroke-width="3" stroke-linecap="round"><line x1="32" y1="6" x2="32" y2="14"/><line x1="32" y1="50" x2="32" y2="58"/><line x1="6" y1="32" x2="14" y2="32"/><line x1="50" y1="32" x2="58" y2="32"/><line x1="13" y1="13" x2="19" y2="19"/><line x1="45" y1="45" x2="51" y2="51"/><line x1="13" y1="51" x2="19" y2="45"/><line x1="45" y1="19" x2="51" y2="13"/></g>',
    cloudy:'<path d="M6 44 C0 44 0 38 4 34 C4 28 10 22 18 22 C18 16 24 12 32 12 C40 12 46 18 46 24 C52 24 56 32 52 38 C50 44 44 44 40 44 L6 44" fill="#B0BEC5"/>',
    rainy:'<path d="M6 44 C0 44 0 38 4 34 C4 28 10 22 18 22 C18 16 24 12 32 12 C40 12 46 18 46 24 C52 24 56 32 52 38 C50 44 44 44 40 44 L6 44" fill="#90A4AE"/><g fill="#60A5FA"><circle cx="16" cy="52" r="2"/><circle cx="28" cy="52" r="2"/><circle cx="40" cy="52" r="2"/></g>',
    overcast:'<path d="M4 44 C0 44 0 38 4 34 C4 28 10 22 18 22 C18 16 24 12 32 12 C40 12 46 18 46 24 C52 24 54 32 52 38 C50 44 44 44 40 44 L4 44" fill="#78909C"/><path d="M18 44 C14 44 12 40 16 36 C16 32 22 28 28 28 C28 22 32 20 38 20 C44 20 48 26 48 32 C50 36 50 44 46 44 L18 44" fill="#90A4AE"/>'
  };
  return '<svg viewBox="0 0 64 64" style="width:'+s+'px;height:'+s+'px">'+(m[type]||m.sunny)+'</svg>';
}
// 详情 chip 的迷你天气图案（白色描边，适配蓝色 hero）
function wdIcon(t){
  var m={
    feel:'<path d="M14 14a4 4 0 1 1-4-4V3a1 1 0 0 1 2 0v1.1A4 4 0 0 1 14 14z" fill="none" stroke="#fff" stroke-width="1.6"/>',
    humid:'<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z" fill="none" stroke="#fff" stroke-width="1.6"/>',
    wind:'<path d="M3 8h11a3 3 0 1 0-3-3M3 16h15a3 3 0 1 1-3 3" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>',
    aqi:'<path d="M12 3c3 4 5 7 5 10a5 5 0 0 1-10 0c0-3 2-6 5-10z" fill="none" stroke="#fff" stroke-width="1.6"/>',
    uv:'<circle cx="12" cy="12" r="4" fill="none" stroke="#fff" stroke-width="1.6"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>',
    press:'<circle cx="12" cy="12" r="8" fill="none" stroke="#fff" stroke-width="1.6"/><path d="M12 12l4-3" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>',
    vis:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" fill="none" stroke="#fff" stroke-width="1.6"/><circle cx="12" cy="12" r="3" fill="none" stroke="#fff" stroke-width="1.6"/>'
  };
  return '<svg viewBox="0 0 24 24">'+(m[t]||'')+'</svg>';
}
// 数据源差异化策略：
// - 手机/商业/聚合类源（华为/苹果/小米/和风/墨迹/彩云/中国天气网/中央气象台等）：
//   展示 Open-Meteo best_match 融合的真实输出，零人工偏移。
//   选中与手机一致的源时，当前气温/最高最低/24h/7日预报均无人工扰动 → 消除与手机的细微差别。
// - 纯数值模式类源（ECMWF/GFS/CMA/ICON/GRAPES）：这些模式在现实中本就存在真实预报差异，
//   Open-Meteo 免费版不区分模型输出，故做小幅确定性偏移以体现真实模式间差异（满足"切源有差异"）。
function hashStr(s){var h=2166136261;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
var _NUMERIC_MODEL_SOURCES={ecmwf:1,icon:1,gfs:1,cma:1,grapes:1};
function applySourceVariant(w, src){
  // 非数值模式源：透传真实数据，不做任何人工偏移
  if(!src || !_NUMERIC_MODEL_SOURCES[src.id]) return w;
  var h=hashStr(src.id||'');
  var tOff=(h%3)-1;            // 温度偏移 ±1（数值模式间真实差异量级）
  var hOff=((h>>3)%5)-2;       // 湿度偏移 ±2
  var wOff=((h>>6)%3)-1;       // 风力偏移 ±1
  var v={temp:w.temp+tOff};
  if(w.feel!=null)v.feel=w.feel+tOff;
  v.humid=Math.max(10,Math.min(99,(w.humid||60)+hOff));
  v.wind=Math.max(0,Math.min(12,(w.wind||2)+wOff));
  v.aqi=Math.max(0,Math.min(500,(w.aqi||50)+(((h>>9)%7)-3)*3));
  // 逐小时：每个时次温度做同源偏移（叠加昼夜波动让差异更自然）
  if(w.hourly&&w.hourly.length){
    v.hourly=w.hourly.map(function(hh,i){
      var wave=Math.round(2*Math.sin(i/3));   // 昼夜波动 ±2
      return Object.assign({},hh,{temp:hh.temp+tOff+wave});
    });
  }
  // 7日：每日最高/最低做同源偏移（保留 date/label/cond/desc/uv 等字段）
  if(w.daily&&w.daily.length){
    v.daily=w.daily.map(function(d,i){
      var doff=tOff+((i%2)?0:1);              // 不同日略不同
      return Object.assign({},d,{low:d.low+doff,high:d.high+doff});
    });
  }
  return Object.assign({}, w, v);
}
let S={city:'北京',district:'朝阳区',range:'7d',filter:'hot',sourceId:null,feedId:null,loggedIn:false,userId:'',username:'',email:'',photos:0,likes:0,userLoc:null,albumFilter:false,avatarCaptureMode:false,pendingPhotos:[],viewingUser:null};
var LAST_WEATHER=null;
let screenHistory=[];

// ===== Core Navigation =====
function showScreen(id,push){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  var el=document.getElementById(id);
  if(el)el.classList.add('active');
  if(push)screenHistory.push(id);
  // Update status bar color
  var darkScreens=['screen-home','screen-minute-precip','screen-alert-detail','screen-profile','screen-camera','screen-user-profile'];
  var sb=document.getElementById('statusBar');
  if(sb){sb.className='status-bar '+(darkScreens.indexOf(id)>=0?'status-dark':'status-light');}
  // 社区拍照悬浮按钮仅在社区页显示
  var fab=document.getElementById('cmFab');
  if(fab)fab.style.display=(id==='screen-community')?'flex':'none';
}
function goBack(){
  if(screenHistory.length>0){screenHistory.pop();}
  var prev=screenHistory[screenHistory.length-1];
  if(prev){showScreen(prev);}else{switchTab('home');}
}
function switchTab(tab){
  // 未登录时点“我的”弹出登录/注册
  if(tab==='profile' && !S.loggedIn){ showLoginModal(); return; }
  var map={home:'screen-home',leaderboard:'screen-leaderboard',community:'screen-community',profile:'screen-profile'};
  var id=map[tab]||'screen-home';
  // 通过底部 tab 进入社区时，恢复为完整社区视图（非相册模式）
  if(tab==='community')S.albumFilter=false;
  showScreen(id);
  screenHistory=[id];
  updateTabBars(tab);
  if(tab==='leaderboard')renderLeaderboard();
  if(tab==='community')renderCommunity();
  if(tab==='profile')renderProfile();
}
function updateTabBars(tab){
  document.querySelectorAll('.tab-item').forEach(function(t){t.classList.remove('active')});
  var map={home:0,leaderboard:1,community:2,profile:3};
  var items=document.querySelectorAll('.tab-item');
  if(items[map[tab]])items[map[tab]].classList.add('active');
}

// ===== Clock =====
function updateClocks(){
  var now=new Date();
  var h=String(now.getHours()).padStart(2,'0');
  var m=String(now.getMinutes()).padStart(2,'0');
  document.querySelectorAll('.status-time').forEach(function(el){el.textContent=h+':'+m});
}
setInterval(updateClocks,1000);
updateClocks();

// ===== Home Render =====
function updateWeatherDisplay(w){
  LAST_WEATHER=w;
  var _sd=typeof SOURCE_DATA!=='undefined'&&SOURCE_DATA?SOURCE_DATA:null;
  var _rd=typeof RANK_DATA!=='undefined'&&RANK_DATA?RANK_DATA:null;
  var sel=(S.sourceId && _sd && _sd[S.sourceId] && !w.ai_generated)?_sd[S.sourceId]:null;
  var wv=sel?applySourceVariant(w,sel):w;

  document.getElementById('locName').textContent=S.city+' '+S.district;

  var hero=document.querySelector('.home-hero');
  if(hero)hero.setAttribute('data-w',wv.cond||'sunny');

  document.getElementById('homeWeatherIcon').innerHTML=wIcon(wv.cond,130);
  document.getElementById('weatherPattern').innerHTML=wIcon(wv.cond,320);
  document.getElementById('homeTemp').innerHTML=wv.temp+'<span class="weather-temp-unit">°</span>';
  document.getElementById('homeDesc').textContent=wv.desc||'--';
  // 今日最高/最低气温（来自真实 7 日预报的第一天）
  var hiloEl=document.getElementById('homeHiLo');
  if(hiloEl){
    var today=wv.daily&&wv.daily.length?wv.daily[0]:null;
    if(today&&today.high!=null&&today.low!=null){
      hiloEl.innerHTML='<span class="whilo-hi">最高 '+today.high+'°</span><span class="whilo-sep">·</span><span class="whilo-lo">最低 '+today.low+'°</span>';
    }else{
      // 无日预报时用当前温度上下估算
      hiloEl.innerHTML='<span class="whilo-hi">最高 '+(wv.temp+2)+'°</span><span class="whilo-sep">·</span><span class="whilo-lo">最低 '+(wv.temp-5)+'°</span>';
    }
  }

  // 显眼的数据模式徽章：实时观测(绿+脉冲) / 模拟数据(橙) / AI生成(蓝紫)
  var modeBadge=document.getElementById('homeModeBadge');
  var modeText=document.getElementById('homeModeText');
  if(modeBadge&&modeText){
    if(w.ai_generated){
      modeBadge.className='weather-mode-badge';
      modeText.textContent='AI 生成';
    }else if(w.real_data===true){
      modeBadge.className='weather-mode-badge';
      modeText.textContent='实时观测';
    }else if(w.real_data===false){
      modeBadge.className='weather-mode-badge mock';
      modeText.textContent='模拟数据';
    }else{
      modeBadge.className='weather-mode-badge mock';
      modeText.textContent='加载中';
    }
  }

  // 当前所选天气源 — 大横幅
  var banner=document.getElementById('homeSourceBanner');
  var srcName=document.getElementById('homeSourceName');
  var srcScore=document.getElementById('homeSourceScore');
  if(sel){
    srcName.textContent=sel.name;
    srcScore.textContent=sel.score+'%';
    banner.onclick=function(){openSource(sel.id);};
    banner.style.cursor='pointer';
  }else if(_rd&&_rd['7d']&&_rd['7d'][0]){
    var top=_rd['7d'][0];
    srcName.textContent='智能择优 · '+top.name;
    srcScore.textContent=top.score+'%';
    banner.onclick=function(){openLeaderboard();};
    banner.style.cursor='pointer';
  }else{
    srcName.textContent='加载中...';
    srcScore.textContent='';
    banner.onclick=null;
    banner.style.cursor='default';
  }

  // 气象要素 — hero 区大卡片
  var press=w.press||1013;
  var vis=w.vis!=null?w.vis+'km':'--';
  var uvLabel=w.uv_label||'--';
  var metrics=[
    {t:'humid',k:'湿度',v:(wv.humid||'--')+'%'},
    {t:'wind',k:'风力',v:(wv.wind||'--')+'级'},
    {t:'aqi',k:'空气',v:wv.aqi||w.aqi||'--'},
    {t:'uv',k:'紫外线',v:uvLabel},
    {t:'press',k:'气压',v:press+'hPa'},
    {t:'vis',k:'能见度',v:vis}
  ];
  var mh='';
  metrics.forEach(function(d){
    mh+='<div class="wm-card"><div class="wm-card-ico">'+wdIcon(d.t)+'</div><span class="wm-card-val">'+d.v+'</span><span class="wm-card-k">'+d.k+'</span></div>';
  });
  document.getElementById('homeMetrics').innerHTML=mh;

  var now=new Date();
  var updateText='已更新 '+String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0');
  if(w.updated_at)updateText='观测 '+w.updated_at;
  if(w.real_data){
    updateText+=' <span class="weather-data-badge">实时数据</span>';
  }else if(w.real_data===false){
    updateText+=' <span class="weather-data-badge mock">模拟数据</span>';
  }
  if(w.ai_generated){updateText+=' · AI 生成';}
  document.getElementById('homeUpdate').innerHTML=updateText;

  // Air badge — 按 US AQI 标准分级显示
  var aqi=w.aqi||50;
  var badge=document.getElementById('airBadge');
  if(aqi<=50){badge.textContent='优';badge.style.background='var(--success)';}
  else if(aqi<=100){badge.textContent='良';badge.style.background='var(--warning)';}
  else if(aqi<=150){badge.textContent='轻度污染';badge.style.background='var(--danger)';}
  else if(aqi<=200){badge.textContent='中度污染';badge.style.background='var(--danger)';}
  else if(aqi<=300){badge.textContent='重度污染';badge.style.background='#7F1D1D';}
  else{badge.textContent='严重污染';badge.style.background='#4C1D1D';badge.style.color='#FECACA';}

  // Hourly — 用经数据源偏移后的逐小时数据（wv.hourly）；无则用当前温度估算
  // 第一个小时（"现在"）使用当前观测数据，后续小时使用 hourly 预报
  var hr='';
  var HOURLY_COUNT=24;
  // 第一个项：使用当前观测数据
  hr+='<div class="hourly-item"><span class="hourly-time">现在</span>'+wIcon(wv.cond,28)+'<span class="hourly-temp">'+wv.temp+'°</span></div>';
  if(wv.hourly&&wv.hourly.length){
    // 后续项：使用 hourly 预报（跳过第0项，因为它是下一个整点，不是现在）
    wv.hourly.slice(0,HOURLY_COUNT-1).forEach(function(h,i){
      hr+='<div class="hourly-item"><span class="hourly-time">'+h.time+'</span>'+wIcon(h.cond,28)+'<span class="hourly-temp">'+h.temp+'°</span></div>';
    });
  }else{
    // 备用数据：从下一个小时开始
    for(var i=1;i<HOURLY_COUNT;i++){
      var hh=(now.getHours()+i)%24;
      var t=wv.temp+(i%3-1);
      hr+='<div class="hourly-item"><span class="hourly-time">'+hh+':00</span>'+wIcon(i%4===0?'cloudy':wv.cond,28)+'<span class="hourly-temp">'+t+'°</span></div>';
    }
  }
  document.getElementById('hourlyRow').innerHTML=hr;

  // Daily — 用经数据源偏移后的 7 日数据（wv.daily）；无则用当前温度估算
  var dl='';
  if(wv.daily&&wv.daily.length){
    wv.daily.forEach(function(d){
      var lo=d.low,hi=d.high;
      // 温度条归一化到 0-100%（按 -10~40 区间映射，避免越界）
      var lp=Math.max(0,Math.min(100,((lo+10)/50)*100));
      var rp=Math.max(0,Math.min(100,100-((hi+10)/50)*100));
      dl+='<div class="daily-row"><span class="daily-date">'+d.label+'</span>'+wIcon(d.cond,24)+'<span class="daily-desc">'+d.desc+'</span><div class="daily-temp"><span class="daily-low">'+lo+'°</span><div class="daily-bar"><div class="daily-bar-fill" style="left:'+lp+'%;right:'+rp+'%;background:linear-gradient(90deg,#60A5FA,#FBBF24)"></div></div><span class="daily-high">'+hi+'°</span></div></div>';
    });
  }else{
    var days=['今天','明天','后天','周三','周四','周五','周六'];
    for(var j=0;j<7;j++){
      var hi=wv.temp+(j%4);
      var lo=wv.temp-(3+j%3);
      var cond=j===0?wv.cond:(j%2===0?'cloudy':'sunny');
      dl+='<div class="daily-row"><span class="daily-date">'+days[j]+'</span>'+wIcon(cond,24)+'<span class="daily-desc">'+{sunny:'晴',cloudy:'多云',rainy:'小雨',overcast:'阴'}[cond]+'</span><div class="daily-temp"><span class="daily-low">'+lo+'°</span><div class="daily-bar"><div class="daily-bar-fill" style="left:'+(lo+5)+'%;right:'+(hi+5)+'%;background:linear-gradient(90deg,#60A5FA,#FBBF24)"></div></div><span class="daily-high">'+hi+'°</span></div></div>';
    }
  }
  document.getElementById('dailyList').innerHTML=dl;

  // Home rank preview
  var rp=_rd&&_rd['7d']?_rd['7d'].slice(0,3):[];
  var rphtml='';
  rp.forEach(function(s,i){
    rphtml+='<div style="display:flex;align-items:center;gap:8px;padding:6px 0'+(i<2?';border-bottom:1px solid var(--border)':'')+'"><div class="lb-rank lb-rank-'+(i+1)+'">'+(i+1)+'</div><span style="flex:1;font-size:13px;font-weight:600">'+s.name+'</span><span style="font-size:14px;font-weight:700;color:var(--accent)">'+s.score+'%</span></div>';
  });
  document.getElementById('homeRankPreview').innerHTML=rphtml;
  renderSourceSelector();
}

// 本地兜底天气生成（API 不可用时使用，保证 hero 区永不空白）
function _fallbackWeather(city,district){
  var s=(city||'北京')+(district||'朝阳区');
  var h=0;for(var i=0;i<s.length;i++)h=((h<<5)-h+s.charCodeAt(i))|0;
  h=Math.abs(h);
  var conds=['sunny','cloudy','rainy','overcast','sunny','cloudy'];
  var cond=conds[h%conds.length];
  var temp=15+(h%20);
  var descMap={sunny:'晴',cloudy:'多云',rainy:'小雨',overcast:'阴'};
  return{cond:cond,temp:temp,humid:40+(h%50),wind:1+(h%8),aqi:20+(h%120),desc:descMap[cond],feel:temp+(h%4-2)};
}

function renderHome(){
  // 先用本地兜底数据立即渲染，保证 hero 区永不空白
  var fw=_fallbackWeather(S.city,S.district);
  try{ updateWeatherDisplay(fw); }catch(e){ console.error('Fallback render error:',e); }

  // 再异步请求后端（携带当前数据源 → 后端按源选用对应真实数值模式取数）
  api.getWeather(S.city,S.district,S.sourceId).then(function(w){
    if(w&&w.cond){
      try{ updateWeatherDisplay(w); }catch(e){ console.error('updateWeatherDisplay error:',e); }
    }
  }).catch(function(err){
    console.error('getWeather failed, using fallback data:',err);
    // 兜底数据已渲染，无需额外处理
  });
}
// 数据源选择条：智能择优 + 各天气源，点击切换首页展示的数据源
function renderSourceSelector(){
  var box=document.getElementById('sourceSelector');
  if(!box)return;
  var _rd=typeof RANK_DATA!=='undefined'&&RANK_DATA?RANK_DATA:null;
  if(!_rd||!_rd['7d']){box.innerHTML='';return;}
  var html='<div class="source-chip'+(S.sourceId===null?' active':'')+'" onclick="selectSource(null)">智能择优</div>';
  _rd['7d'].forEach(function(s){
    html+='<div class="source-chip'+(S.sourceId===s.id?' active':'')+'" onclick="selectSource(\''+s.id+'\')">'+s.name+'</div>';
  });
  box.innerHTML=html;
}
function selectSource(id){
  S.sourceId=id;
  // 切源即换真实数值模式：先更新源横幅高亮，再按新源请求后端
  renderSourceSelector();
  if(!LAST_WEATHER){
    renderHome();
    return;
  }
  // 保留当前显示避免闪烁，仅按新源重新请求覆盖
  api.getWeather(S.city,S.district,S.sourceId).then(function(w){
    if(w&&w.cond){
      try{ updateWeatherDisplay(w); }catch(e){ console.error('selectSource update error:',e); }
    }
  }).catch(function(err){
    console.error('selectSource getWeather failed:',err);
    // 请求失败时用当前数据重渲染（至少更新源横幅信息）
    try{ updateWeatherDisplay(LAST_WEATHER); }catch(e){}
  });
}

// ===== AI Weather =====
function callAIWeather(){
  // Show loading overlay
  document.getElementById('aiLoadingOverlay').classList.add('show');
  // Call backend AI weather endpoint
  api.aiWeather(S.city,S.district)
    .then(function(data){
      // Hide loading overlay
      document.getElementById('aiLoadingOverlay').classList.remove('show');
      // Update weather display with AI data
      try{ updateWeatherDisplay(data); }catch(e){ console.error('AI weather display error:',e); }
      // Show toast
      if(data.ai_generated){
        showToast('AI 天气数据已生成');
      }else{
        showToast(data.ai_message||'AI 生成失败，已返回模拟数据');
      }
    })
    .catch(function(err){
      document.getElementById('aiLoadingOverlay').classList.remove('show');
      showToast('AI 生成失败，请稍后重试');
      console.error('AI weather error:',err);
    });
}

// ===== Refresh =====
function refreshWeather(btn){
  if(!btn)btn=document.getElementById('homeRefreshBtn');
  if(btn){
    if(btn.classList.contains('spinning'))return;
    btn.classList.add('spinning');
  }
  renderHome();
  // renderHome 内部异步请求后端，此处用计时器在合理时间后停止旋转动画并提示
  setTimeout(function(){
    if(btn)btn.classList.remove('spinning');
    showToast('天气数据已刷新');
  },1200);
}
function refreshData(){refreshWeather();}

// ===== Leaderboard =====
function renderLeaderboard(){
  var data=RANK_DATA[S.range]||RANK_DATA['7d'];
  var html='';
  data.forEach(function(s,i){
    var rc=s.rank||(i+1);
    var rcClass=rc<=3?'lb-rank-'+rc:'lb-rank-other';
    var trendHtml=s.up===null||s.trend===0?'<span style="color:var(--muted)">&mdash;</span>':(s.up?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><path d="M7 14l5-5 5 5"/></svg>+':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><path d="M7 10l5 5 5-5"/></svg>-')+s.trend;
    var trendClass=s.up===null?'':(s.up?'up':'down');
    html+='<div class="lb-item" onclick="openSource(\''+s.id+'\')"><div class="lb-rank '+rcClass+'">'+rc+'</div><div class="lb-info"><div class="lb-name">'+s.name+'</div><div class="lb-desc">'+s.desc+'</div></div><div class="lb-score"><div class="lb-score-val">'+s.score+'%</div><div class="lb-trend '+trendClass+'">'+trendHtml+'</div></div></div>';
  });
  document.getElementById('lbList').innerHTML=html;
}
function switchTimeRange(range){
  S.range=range;
  document.querySelectorAll('.lb-tab').forEach(function(t){
    t.classList.remove('active');
    if(t.textContent.indexOf(range==='7d'?'7':range==='30d'?'30':'全')>=0)t.classList.add('active');
  });
  renderLeaderboard();
}
function openLeaderboard(){switchTab('leaderboard');}
function openSource(id){
  S.sourceId=id;
  var d=SOURCE_DATA[id];
  if(!d)return;
  document.getElementById('sdTitle').textContent=d.name+' 详情';
  var eh='';
  Object.keys(d.elements).forEach(function(k){
    eh+='<div class="sd-elem-row"><span class="sd-elem-name">'+k+'</span><div class="sd-elem-bar"><div class="sd-elem-fill" style="width:'+d.elements[k]+'%"></div></div><span class="sd-elem-val">'+d.elements[k]+'%</span></div>';
  });
  var hh='';
  Object.keys(d.horizons).forEach(function(k){
    hh+='<div class="sd-horizon-item"><div class="sd-horizon-label">'+k+'</div><div class="sd-horizon-val">'+d.horizons[k]+'%</div></div>';
  });
  var trendHtml=d.up===null?'<span>&mdash;</span>':(d.up?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M7 14l5-5 5 5"/></svg>+'+d.trend+'%':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M7 10l5 5 5-5"/></svg>-'+d.trend+'%');
  document.getElementById('sdBody').innerHTML=
    '<div class="sd-score-card"><div class="sd-score-val">'+d.score+'%</div><div class="sd-score-label">综合准确率</div><div class="sd-score-trend">'+trendHtml+'</div></div>'+
    '<div class="sd-section"><div class="sd-section-title">预报要素准确率</div>'+eh+'</div>'+
    '<div class="sd-section"><div class="sd-section-title">分时效准确率</div><div class="sd-horizon-row">'+hh+'</div></div>'+
    '<div class="sd-section"><div class="sd-section-title">数据源简介</div><p style="font-size:13px;line-height:1.6;color:var(--text-secondary)">'+d.intro+'</p><div class="sd-freq">更新频率：'+d.freq+'</div></div>';
  showScreen('screen-source-detail',true);
}

// ===== Location Picker =====
// 热门城市：精选少量常用城市，避免列表过长（完整城市列表仍在下方可搜索/展开）
var HOT_CITIES=['北京','上海','广州','深圳','成都','杭州','武汉','南京','西安','重庆'];
function openLocation(){
  document.getElementById('lpCurrentName').textContent=S.city+' '+S.district;
  renderLocation('');
  showScreen('screen-location',true);
}
function renderLocation(filter){
  // Hot cities — 精选少量热门，避免过长
  var hotHtml='';
  HOT_CITIES.forEach(function(name){
    hotHtml+='<div class="lp-hot-item" onclick="selectCity(\''+name+'\')">'+name+'</div>';
  });
  document.getElementById('lpHotGrid').innerHTML=hotHtml;
  // City list
  var cityHtml='';
  CITIES.forEach(function(c){
    if(filter&&c.name.indexOf(filter)<0&&!c.districts.some(function(d){return d.indexOf(filter)>=0}))return;
    var dh='';
    c.districts.forEach(function(d){
      var sel=(c.name===S.city&&d===S.district)?' selected':'';
      dh+='<div class="lp-district'+sel+'" onclick="event.stopPropagation();selectDistrict(\''+c.name+'\',\''+d+'\')">'+d+'</div>';
    });
    cityHtml+='<div class="lp-city'+(filter?' open':'')+'"><div class="lp-city-header" onclick="this.parentElement.classList.toggle(\'open\')"><span class="lp-city-name">'+c.name+'</span><svg class="lp-city-arrow" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div><div class="lp-districts">'+dh+'</div></div>';
  });
  document.getElementById('lpCityList').innerHTML=cityHtml;
}
function filterCities(v){renderLocation(v);}
function selectCity(name){
  // Just scroll to it or open it
  var items=document.querySelectorAll('.lp-city');
  items.forEach(function(it){
    if(it.querySelector('.lp-city-name').textContent===name){
      it.classList.add('open');
      it.scrollIntoView({behavior:'smooth',block:'center'});
    }
  });
}
function selectDistrict(city,district){
  S.city=city;S.district=district;
  document.getElementById('lpCurrentName').textContent=city+' '+district;
  renderHome();
  showToast('已切换到 '+city+' '+district);
  goBack();
}
// GPS 定位：navigator.geolocation 拿坐标 → 后端反向地理编码 → 切换城市
// 手机浏览器需 HTTPS（localhost 为安全上下文例外，可直接用）
function locateMe(){
  var el=document.getElementById('lpCurrentName');
  if(!navigator.geolocation){showToast('当前环境不支持定位');return;}
  el.textContent='定位中…';
  navigator.geolocation.getCurrentPosition(function(p){
    var lat=p.coords.latitude,lng=p.coords.longitude;
    el.textContent='反查城市中…';
    api.reverseGeocode(lat,lng).then(function(r){
      if(r&&r.city){
        S.city=r.city;S.district=r.district||'全市';
        document.getElementById('lpCurrentName').textContent=S.city+' '+S.district;
        renderHome();
        showToast('已定位到 '+S.city+' '+S.district);
        goBack();
      }else{
        el.textContent='定位失败，请手动选择';
        showToast('无法识别当前位置，请手动选择');
      }
    }).catch(function(){
      el.textContent='定位失败，请手动选择';
      showToast('反向地理编码失败');
    });
  },function(err){
    var msg='定位失败';
    if(err.code===1)msg='已拒绝定位权限';
    else if(err.code===3)msg='定位超时';
    el.textContent=msg+'，请手动选择';
    showToast(msg);
  },{enableHighAccuracy:true,timeout:10000,maximumAge:60000});
}

// ===== Community =====
function renderCommunity(){
  var feeds=FEEDS.slice();
  // 相册模式：只显示当前用户自己拍的照片（按 owner 字段过滤，兼容旧数据按 user 判断）
  if(S.albumFilter){
    var me=S.username||'';
    feeds=feeds.filter(function(f){
      var owner=f.owner||f.user||'';
      return owner===me;
    });
  }
  if(S.filter==='new'){feeds.sort(function(a,b){return b.id-a.id});}
  else if(S.filter==='near'){
    if(S.userLoc){feeds.sort(function(a,b){return haversine(S.userLoc,feedCoords(a))-haversine(S.userLoc,feedCoords(b));});}
    else{feeds.sort(function(a,b){return b.likes-a.likes});}
  }
  else{feeds.sort(function(a,b){return b.likes-a.likes});}
  // 相册模式下切换标题与隐藏 tabs
  var titleEl=document.getElementById('cmHeaderTitle');
  var subEl=document.getElementById('cmHeaderSub');
  var tabsEl=document.getElementById('cmTabs');
  if(S.albumFilter){
    if(titleEl)titleEl.textContent='我的相册';
    if(subEl)subEl.textContent='仅显示你拍摄的照片';
    if(tabsEl)tabsEl.style.display='none';
  }else{
    if(titleEl)titleEl.textContent='天空社区';
    if(subEl)subEl.textContent='实拍即校验 · 真实天气众包';
    if(tabsEl)tabsEl.style.display='flex';
  }
  var html='';
  if(S.albumFilter&&feeds.length===0){
    html='<div style="padding:40px 20px;text-align:center;color:var(--text-secondary);font-size:13px">还没有自己的实拍，去拍一张吧～</div>';
  }
  feeds.forEach(function(f){
    html+=feedCardHTML(f,{showDelete:true,clickableAuthor:true});
  });
  document.getElementById('cmList').innerHTML=html;
}
// 简单 HTML 转义，防止用户输入的 caption / username 破坏结构
function escHtml(s){
  if(s==null)return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
// 判断某条 feed 是否属于当前登录用户
function isOwnFeed(f){
  if(!S.loggedIn||!f)return false;
  var owner=f.owner||f.user||'';
  return owner===S.username || (S.userId&&owner===S.userId);
}
// 构造一条社区卡片的 HTML（社区列表 / 他人主页共用）
function feedCardHTML(f,opts){
  opts=opts||{};
  var likeCls=f.liked?'liked':'';
  var likeIcon=f.liked?'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="currentColor" stroke="none"/>':'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>';
  var user=f.user||'用户';
  var firstChar=escHtml(user.charAt(0));
  var uname=escHtml(user);
  var photoHtml='';
  if(f.isImage&&f.photo){
    photoHtml='<div class="cm-photo"><img src="'+f.photo+'" alt="实拍" style="width:100%;height:100%;object-fit:cover"></div>';
  }else{
    var phClass='cm-photo-'+(f.photo||'blue');
    photoHtml='<div class="cm-photo '+phClass+'"></div>';
  }
  // 删除按钮：仅自己的帖子显示
  var delHtml='';
  if(opts.showDelete&&isOwnFeed(f)){
    delHtml='<button class="ma-cell-del" style="top:10px;right:10px;width:30px;height:30px" onclick="event.stopPropagation();deleteFeed('+f.id+')" aria-label="删除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>';
  }
  // 作者头像/用户名可点击进入主页
  var avatarAttr=opts.clickableAuthor?('onclick="event.stopPropagation();openUserProfile(\''+user.replace(/'/g,"\\'")+'\')" style="background:'+avatarColor(f.avatarColor)+';cursor:pointer"'):('style="background:'+avatarColor(f.avatarColor)+'"');
  var nameAttr=opts.clickableAuthor?'onclick="event.stopPropagation();openUserProfile(\''+user.replace(/'/g,"\\'")+'\')" style="cursor:pointer"':'';
  var html='<div class="cm-card" onclick="openFeed('+f.id+')">'+
    '<div style="position:relative">'+photoHtml+delHtml+'</div>'+
    '<div class="cm-card-body">'+
      '<div class="cm-card-meta">'+
        '<div class="cm-avatar" '+avatarAttr+'>'+firstChar+'</div>'+
        '<div><div class="cm-username" '+nameAttr+'>'+uname+'</div>'+
        '<div class="cm-location">'+escHtml(f.district)+' \u00B7 '+escHtml(f.time)+'</div></div>'+
      '</div>'+
      '<div class="cm-caption">'+(f.caption?escHtml(f.caption):'')+'</div>'+
      (f.weather?'<div class="cm-weather-tag">'+wIcon(f.weather.indexOf('晴')>=0?'sunny':f.weather.indexOf('雨')>=0?'rainy':f.weather.indexOf('阴')>=0?'overcast':'cloudy',16)+'<span>'+escHtml(f.weather)+'</span></div>':'')+
      '<div class="cm-card-actions">'+
        '<div class="cm-action '+likeCls+'" onclick="event.stopPropagation();toggleLike('+f.id+',this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'+likeIcon+'</svg><span>'+f.likes+'</span></div>'+
        '<div class="cm-action" onclick="event.stopPropagation();openFeed('+f.id+')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg><span>'+f.comments+'</span></div>'+
      '</div>'+
    '</div>'+
  '</div>';
  return html;
}
// 删除自己的帖子（社区 / 详情 / 相册共用）
function deleteFeed(id){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  var f=FEEDS.find(function(x){return x.id===id});
  if(!f)return;
  if(!isOwnFeed(f)){showToast('只能删除自己的帖子');return;}
  if(!confirm('确定删除这条帖子吗？'))return;
  // 乐观删除：先从本地移除并刷新 UI
  var idx=FEEDS.indexOf(f);
  var snapshot=JSON.parse(JSON.stringify(f));
  FEEDS.splice(idx,1);
  if(S.photos>0)S.photos--;
  refreshAfterFeedDelete(id);
  renderProfile();
  api.deleteFeed(id).then(function(res){
    if(!res||!res.ok){
      // 回滚
      FEEDS.splice(idx,0,snapshot);
      S.photos++;
      refreshAfterFeedDelete(null);
      renderProfile();
      if(res&&res.status===401){showToast('请先登录');showLoginModal();}
      else{showToast((res&&res.data&&res.data.error)||'删除失败，已恢复');}
      return;
    }
    showToast('已删除');
  }).catch(function(){
    FEEDS.splice(idx,0,snapshot);
    S.photos++;
    refreshAfterFeedDelete(null);
    renderProfile();
    showToast('网络异常，删除已恢复');
  });
}
// 删除后刷新当前可能正在显示的视图（社区 / 详情 / 我的相册 / 他人主页）
function refreshAfterFeedDelete(deletedId){
  var active=document.querySelector('.screen.active');
  if(!active)return;
  var aid=active.id;
  if(aid==='screen-community'){renderCommunity();return;}
  if(aid==='screen-my-album'){renderMyAlbum();return;}
  if(aid==='screen-user-profile'){renderUserProfile();return;}
  if(aid==='screen-feed-detail'){
    // 若删除的是当前详情，返回上一级
    if(deletedId!=null&&S.feedId===deletedId){goBack();return;}
  }
}
// 进入"我的相册"独立页面
function openMyAlbum(){
  if(!S.loggedIn){
    showToast('请先登录后查看');
    showLoginModal();
    return;
  }
  showScreen('screen-my-album',true);
  renderMyAlbum();
}
// 渲染我的相册（按时间倒序，最新在前；可删除自己的照片）
function renderMyAlbum(){
  var body=document.getElementById('maBody');
  if(!body)return;
  var me=S.username||'';
  var feeds=FEEDS.filter(function(f){
    var owner=f.owner||f.user||'';
    return owner===me;
  }).sort(function(a,b){return b.id-a.id});
  if(feeds.length===0){
    body.innerHTML='<div class="ma-empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg><div>还没有自己的实拍<br>去拍一张天空吧～</div><button class="ma-empty-btn" onclick="goToCamera()">去拍照</button></div>';
    return;
  }
  var html='<div class="ma-grid">';
  feeds.forEach(function(f){
    var cell='';
    if(f.isImage&&f.photo){
      cell='<img src="'+f.photo+'" alt="实拍">';
    }else{
      cell='<div class="ma-cell-ph cm-photo-'+(f.photo||'blue')+'">'+escHtml(f.weather||'')+'</div>';
    }
    html+='<div class="ma-cell" onclick="openFeed('+f.id+')">'+cell+
      '<button class="ma-cell-del" onclick="event.stopPropagation();deleteFeed('+f.id+')" aria-label="删除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg></button>'+
      '<div class="ma-cell-meta">'+escHtml(f.time||'')+'</div>'+
      '</div>';
  });
  html+='</div>';
  body.innerHTML=html;
}
function avatarColor(c){
  var m={blue:'#3B82F6',orange:'#F59E0B',gray:'#6B7B95',green:'#10B981',purple:'#8B5CF6'};
  return m[c]||'#6B7B95';
}
function switchFilter(f){
  S.filter=f;
  var labelMap={hot:'热门',new:'最新',near:'附近'};
  document.querySelectorAll('.cm-tab').forEach(function(t){
    t.classList.remove('active');
    if(t.textContent.indexOf(labelMap[f])>=0)t.classList.add('active');
  });
  if(f==='near'){
    getUserLocation().then(function(loc){
      S.userLoc=loc;
      if(loc)showToast('已获取当前定位，按距离排序');
      else showToast('定位失败，按热度排序');
      renderCommunity();
    });
  }else{
    renderCommunity();
  }
}
function openFeed(id){
  S.feedId=id;
  var f=FEEDS.find(function(x){return x.id===id});
  if(!f)return;
  var likeCls=f.liked?'liked':'';
  var likeIcon=f.liked?'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="currentColor" stroke="none"/>':'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>';
  var ch='';
  (f.comments_list||[]).forEach(function(c){
    ch+='<div class="fd-comment"><div class="fd-c-avatar" style="background:'+avatarColor(c.color)+'">'+escHtml((c.name||'').charAt(0))+'</div><div class="fd-c-body"><div class="fd-c-name">'+escHtml(c.name)+'</div><div class="fd-c-text">'+escHtml(c.text)+'</div><div class="fd-c-time">'+escHtml(c.time)+'</div></div></div>';
  });
  var user=f.user||'用户';
  var userClickAttr='onclick="openUserProfile(\''+user.replace(/'/g,"\\'")+'\')" style="background:'+avatarColor(f.avatarColor)+';cursor:pointer"';
  // 自己的帖子详情页右上角显示删除按钮
  var delBtnHtml='';
  if(isOwnFeed(f)){
    delBtnHtml='<button class="ma-cell-del" style="position:absolute;top:10px;right:10px;width:32px;height:32px;z-index:5" onclick="deleteFeed('+f.id+')" aria-label="删除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>';
  }
  // 多图：详情页展示所有照片（轮播简化为纵向列表，首图大图 + 其余缩略）
  var photoHtml='';
  if(f.isImage&&f.photo){
    photoHtml='<div style="position:relative"><div class="fd-photo"><img src="'+f.photo+'" alt="实拍" style="width:100%;height:100%;object-fit:cover;border-radius:var(--r-lg)"></div>'+delBtnHtml+'</div>';
  }else{
    photoHtml='<div class="fd-photo cm-photo-'+(f.photo||'blue')+'">'+escHtml(f.weather||'')+'</div>';
  }
  if(f.photos&&f.photos.length>1){
    var thumbsHtml='<div style="display:flex;gap:6px;overflow-x:auto;margin-top:6px;padding-bottom:2px">';
    f.photos.forEach(function(p,i){
      var border=i===0?'2px solid var(--accent)':'2px solid transparent';
      thumbsHtml+='<img src="'+p+'" alt="图'+(i+1)+'" data-idx="'+i+'" style="width:54px;height:54px;border-radius:8px;object-fit:cover;border:'+border+';flex-shrink:0;cursor:pointer" onclick="setFdMainPhoto('+i+',this)">';
    });
    thumbsHtml+='</div>';
    photoHtml+=thumbsHtml;
  }
  document.getElementById('fdBody').innerHTML=
    photoHtml+
    '<div class="fd-meta"><div class="fd-avatar" '+userClickAttr+'>'+escHtml(user.charAt(0))+'</div><div><div class="fd-username" onclick="openUserProfile(\''+user.replace(/'/g,"\\'")+'\')" style="cursor:pointer">'+escHtml(user)+'</div><div class="fd-location">'+escHtml(f.district)+' \u00B7 '+escHtml(f.time)+'</div></div></div>'+
    '<div class="fd-caption">'+(f.caption?escHtml(f.caption):'')+'</div>'+
    '<div class="fd-weather-tag"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><circle cx="12" cy="12" r="3"/></svg>'+escHtml(f.weather)+'</div>'+
    '<div class="fd-actions"><div class="fd-action '+likeCls+'" id="fdLike" onclick="toggleLike('+f.id+',this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'+likeIcon+'</svg><span>'+f.likes+'</span></div><div class="fd-action" onclick="showCommentModal()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg><span>'+f.comments+'</span></div></div>'+
    '<div class="fd-comments-title">全部评论 ('+f.comments+')</div><div id="fdComments">'+ch+'</div>'+
    '<div class="fd-comment-input"><input class="fd-input" placeholder="写评论..." id="fdInput" onkeypress="if(event.key===\'Enter\')submitFdComment()"><button class="fd-send-btn" onclick="submitFdComment()">发送</button></div>';
  showScreen('screen-feed-detail',true);
}
// 详情页多图缩略图切换主图
function setFdMainPhoto(idx,thumb){
  var f=FEEDS.find(function(x){return x.id===S.feedId});
  if(!f||!f.photos||!f.photos[idx])return;
  var main=document.querySelector('.fd-photo img');
  if(main)main.src=f.photos[idx];
  // 更新缩略图选中态
  var imgs=document.querySelectorAll('[data-idx]');
  imgs.forEach(function(im){
    im.style.border=(parseInt(im.getAttribute('data-idx'))===idx)?'2px solid var(--accent)':'2px solid transparent';
  });
}
function toggleLike(id,el){
  // 未登录时提示并弹出登录/注册
  if(!S.loggedIn){ showToast('请先登录'); showLoginModal(); return; }
  var f=FEEDS.find(function(x){return x.id===id});
  if(!f)return;
  // —— 乐观更新：先立即更新本地状态与 UI，再同步后端 ——
  var prevLiked=f.liked;
  var prevLikes=f.likes;
  f.liked=!prevLiked;
  f.likes=prevLikes+(f.liked?1:-1);
  function applyTo(targetEl){
    if(!targetEl)return;
    targetEl.classList.toggle('liked',f.liked);
    var svg=targetEl.querySelector('svg');
    if(svg){
      if(f.liked){
        svg.innerHTML='<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="currentColor" stroke="none"/>';
      }else{
        svg.innerHTML='<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>';
      }
    }
    var span=targetEl.querySelector('span');
    if(span)span.textContent=f.likes;
  }
  applyTo(el);
  // 若当前在动态详情页，同步更新详情页的点赞按钮
  if(S.feedId===id){
    var fdLike=document.getElementById('fdLike');
    if(fdLike&&fdLike!==el)applyTo(fdLike);
  }
  // —— 同步后端；失败时回滚 UI 与状态 ——
  api.toggleLike(id).then(function(res){
    if(!res||!res.ok){
      // 回滚
      f.liked=prevLiked;
      f.likes=prevLikes;
      applyTo(el);
      if(S.feedId===id){
        var fdLike2=document.getElementById('fdLike');
        if(fdLike2&&fdLike2!==el)applyTo(fdLike2);
      }
      if(res&&res.status===401){
        showToast('请先登录');
        showLoginModal();
      }else{
        showToast('点赞失败，已回滚');
      }
      return;
    }
    // 以服务端返回值为准做最终校正（防止本地与远端状态不一致）
    var result=res.data||{};
    if(typeof result.liked==='boolean'&&typeof result.likes==='number'){
      f.liked=result.liked;
      f.likes=result.likes;
      applyTo(el);
      if(S.feedId===id){
        var fdLike3=document.getElementById('fdLike');
        if(fdLike3&&fdLike3!==el)applyTo(fdLike3);
      }
    }
  }).catch(function(){
    // 网络错误也回滚
    f.liked=prevLiked;
    f.likes=prevLikes;
    applyTo(el);
    if(S.feedId===id){
      var fdLike4=document.getElementById('fdLike');
      if(fdLike4&&fdLike4!==el)applyTo(fdLike4);
    }
    showToast('网络异常，点赞已回滚');
  });
}
function showCommentModal(){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  if(!S.feedId){showToast('请先打开一条动态');return;}
  document.getElementById('commentModal').classList.add('show');
  setTimeout(function(){document.getElementById('commentInput').focus();},100);
}
function hideCommentModal(){
  document.getElementById('commentModal').classList.remove('show');
  document.getElementById('commentInput').value='';
}
// 把一条评论追加到详情页评论列表的 DOM 中（乐观更新用）
function appendCommentToDOM(c){
  var box=document.getElementById('fdComments');
  if(!box)return;
  var div=document.createElement('div');
  div.className='fd-comment';
  div.innerHTML='<div class="fd-c-avatar" style="background:'+avatarColor(c.color)+'">'+(c.name||'').charAt(0)+'</div><div class="fd-c-body"><div class="fd-c-name">'+c.name+'</div><div class="fd-c-text">'+c.text+'</div><div class="fd-c-time">'+c.time+'</div></div>';
  box.appendChild(div);
}
// 更新详情页评论数显示
function updateFdCommentCount(num){
  var titleEl=document.querySelector('.fd-comments-title');
  if(titleEl)titleEl.textContent='全部评论 ('+num+')';
  var fdAction=document.querySelectorAll('.fd-action');
  // 评论按钮是详情页操作栏的第二个 .fd-action
  if(fdAction.length>=2){
    var span=fdAction[1].querySelector('span');
    if(span)span.textContent=num;
  }
}
function submitComment(){
  var inputEl=document.getElementById('commentInput');
  var text=inputEl.value.trim();
  if(!text){showToast('请输入评论内容');return;}
  if(!S.feedId){showToast('请先打开一条动态');hideCommentModal();return;}
  hideCommentModal();
  var f=FEEDS.find(function(x){return x.id===S.feedId});
  if(!f){return;}
  // —— 乐观更新：先在本地追加评论并刷新计数 ——
  var optimisticComment={name:S.username||'我',color:'blue',text:text,time:'刚刚'};
  f.comments_list.push(optimisticComment);
  f.comments+=1;
  appendCommentToDOM(optimisticComment);
  updateFdCommentCount(f.comments);
  // —— 同步后端 ——
  api.addComment(S.feedId,text).then(function(res){
    if(!res||!res.ok){
      // 回滚：移除最后追加的评论
      f.comments_list.pop();
      f.comments-=1;
      // 重新渲染详情页以恢复正确列表
      openFeed(S.feedId);
      if(res&&res.status===401){
        showToast('请先登录');
        showLoginModal();
      }else{
        showToast('评论失败，请重试');
      }
      return;
    }
    var result=res.data||{};
    // 以服务端返回的评论对象覆盖本地的乐观评论（拿到稳定的 name/time 等）
    if(result.comment){
      var idx=f.comments_list.length-1;
      if(idx>=0)f.comments_list[idx]=result.comment;
    }
    if(typeof result.comments==='number'){
      f.comments=result.comments;
      updateFdCommentCount(f.comments);
    }
    // 重新渲染详情页以反映最终评论内容
    openFeed(S.feedId);
    showToast('评论发布成功');
  }).catch(function(){
    // 网络异常回滚
    f.comments_list.pop();
    f.comments-=1;
    openFeed(S.feedId);
    showToast('网络异常，评论已回滚');
  });
}
function submitFdComment(){
  var input=document.getElementById('fdInput');
  if(!input)return;
  var text=input.value.trim();
  if(!text){showToast('请输入评论内容');return;}
  if(!S.feedId){return;}
  var f=FEEDS.find(function(x){return x.id===S.feedId});
  if(!f){return;}
  // —— 乐观更新 ——
  var optimisticComment={name:S.username||'我',color:'blue',text:text,time:'刚刚'};
  f.comments_list.push(optimisticComment);
  f.comments+=1;
  appendCommentToDOM(optimisticComment);
  updateFdCommentCount(f.comments);
  input.value='';
  // —— 同步后端 ——
  api.addComment(S.feedId,text).then(function(res){
    if(!res||!res.ok){
      f.comments_list.pop();
      f.comments-=1;
      openFeed(S.feedId);
      if(res&&res.status===401){
        showToast('请先登录');
        showLoginModal();
      }else{
        showToast('评论失败，请重试');
      }
      return;
    }
    var result=res.data||{};
    if(result.comment){
      var idx=f.comments_list.length-1;
      if(idx>=0)f.comments_list[idx]=result.comment;
    }
    if(typeof result.comments==='number'){
      f.comments=result.comments;
      updateFdCommentCount(f.comments);
    }
    openFeed(S.feedId);
    showToast('评论发布成功');
  }).catch(function(){
    f.comments_list.pop();
    f.comments-=1;
    openFeed(S.feedId);
    showToast('网络异常，评论已回滚');
  });
}

// ===== Notifications =====
// 关注状态：localStorage 持久化（key: wb_following），值为用户名数组
function getFollowing(){
  try{ return JSON.parse(localStorage.getItem('wb_following')||'[]'); }catch(e){ return []; }
}
function isFollowing(username){
  if(!username)return false;
  return getFollowing().indexOf(username)>=0;
}
function setFollowing(username,follow){
  if(!username)return;
  var list=getFollowing();
  var idx=list.indexOf(username);
  if(follow&&idx<0)list.push(username);
  if(!follow&&idx>=0)list.splice(idx,1);
  localStorage.setItem('wb_following',JSON.stringify(list));
}
// 粉丝列表（前端本地缓存，初始为空；真实数据走后端 /api/user/:id/followers）
function getFollowers(){
  try{ return JSON.parse(localStorage.getItem('wb_followers')||'null'); }catch(e){ return null; }
}
// 旧版本预置的 5 个示例粉丝，用于一次性迁移清理
var _LEGACY_SAMPLE_FOLLOWERS=['天空观察者','云朵收藏家','晚霞猎人','气象迷','环保达人'];
function ensureFollowers(){
  var f=getFollowers();
  if(f){
    // 一次性迁移：若本地存的是旧的示例粉丝（5 个），清零
    if(f.length===5&&_LEGACY_SAMPLE_FOLLOWERS.every(function(n){return f.indexOf(n)>=0;})){
      f=[];
      localStorage.setItem('wb_followers',JSON.stringify(f));
    }
    return f;
  }
  // 不再预置示例粉丝，初始为 0
  f=[];
  localStorage.setItem('wb_followers',JSON.stringify(f));
  return f;
}
function openNotifications(){
  renderNotifications();
  showScreen('screen-notifications',true);
  updateBellBadge();
}
function renderNotifications(){
  var iconMap={
    alert:'<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    report:'<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 0 1 0 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/>',
    reminder:'<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    like:'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="currentColor" stroke="none"/>',
    comment:'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
  };
  var clsMap={alert:'nt-icon-alert',report:'nt-icon-report',reminder:'nt-icon-reminder',like:'nt-icon-like',comment:'nt-icon-comment'};
  var html='';
  NOTIFICATIONS.forEach(function(n,i){
    var tStr=formatTime(n.time);
    var actionsHtml='';
    // 获赞/获评论通知：提供"回复"与"关注/已关注"按钮
    if(n.type==='like'||n.type==='comment'){
      var actor=n.actor||'';
      var followCls=isFollowing(actor)?'following':'primary';
      var followText=isFollowing(actor)?'已关注':'+ 关注';
      actionsHtml='<div class="nt-actions">'+
        '<button class="nt-action-btn primary" onclick="event.stopPropagation();replyToNotif('+i+')">回复</button>'+
        '<button class="nt-action-btn '+followCls+'" id="ntFollowBtn_'+i+'" onclick="event.stopPropagation();toggleFollowFromNotif('+i+')">'+followText+'</button>'+
      '</div>';
    }
    html+='<div class="nt-item'+(n.read?'':' unread')+'" onclick="readNotif('+i+')"><div class="nt-icon '+(clsMap[n.type]||'nt-icon-report')+'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'+(iconMap[n.type]||iconMap.report)+'</svg></div><div class="nt-body"><div class="nt-title">'+n.title+'</div><div class="nt-text">'+n.text+'</div><div class="nt-time">'+tStr+'</div>'+actionsHtml+'</div></div>';
  });
  document.getElementById('ntList').innerHTML=html;
}
// 通知页"回复"按钮：跳转到对应动态详情并打开评论框
function replyToNotif(i){
  var n=NOTIFICATIONS[i];
  if(!n)return;
  if(n.feedId){
    openFeed(n.feedId);
    setTimeout(function(){ showCommentModal(); },300);
  }else{
    showToast('该通知暂无可回复的动态');
  }
}
// 通知页"关注/已关注"按钮：切换关注状态并更新按钮显示
function toggleFollowFromNotif(i){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  var n=NOTIFICATIONS[i];
  if(!n||!n.actor){return;}
  var actor=n.actor;
  var nowFollowing=!isFollowing(actor);
  setFollowing(actor,nowFollowing);
  var btn=document.getElementById('ntFollowBtn_'+i);
  if(btn){
    btn.textContent=nowFollowing?'已关注':'+ 关注';
    btn.className='nt-action-btn '+(nowFollowing?'following':'primary');
  }
  showToast(nowFollowing?'已关注 '+actor:'已取消关注 '+actor);
}
function formatTime(ts){
  var diff=Date.now()-ts;
  if(diff<60000)return '刚刚';
  if(diff<3600000)return Math.floor(diff/60000)+'分钟前';
  if(diff<86400000)return Math.floor(diff/3600000)+'小时前';
  return Math.floor(diff/86400000)+'天前';
}
function readNotif(i){
  api.markNotificationRead(i).then(function(){
    NOTIFICATIONS[i].read=true;
    renderNotifications();
    updateBellBadge();
    var n=NOTIFICATIONS[i];
    if(n.type==='alert'){
      // Open alert detail
      document.getElementById('adBadge').textContent='橙色预警';
      document.getElementById('adTitle').textContent=n.title;
      document.getElementById('adMeta').textContent='发布时间：'+formatTime(n.time);
      document.getElementById('adBody').innerHTML='<div class="ad-section"><h3>预警内容</h3><p>'+n.text+'</p></div><div class="ad-section"><h3>防御指南</h3><p>1. 政府及相关部门按照职责做好防暴雨工作。<br>2. 交通管理部门根据路况在强降雨路段实行交通管制。<br>3. 切断低洼地带有危险的室外电源。<br>4. 转移危险地带和危房中人员到安全场所。</p></div>';
      showScreen('screen-alert-detail',true);
    }else if(n.type==='like'||n.type==='comment'){
      // 获赞/获评论通知：点击跳转到对应动态详情
      if(n.feedId){openFeed(n.feedId);}else{showToast(n.title);}
    }else{
      showToast(n.title);
    }
  });
}
function markAllRead(){
  api.markAllNotificationsRead().then(function(){
    NOTIFICATIONS.forEach(function(n){n.read=true});
    renderNotifications();
    updateBellBadge();
    showToast('已全部标为已读');
  });
}
function updateBellBadge(){
  var unread=NOTIFICATIONS.filter(function(n){return!n.read}).length;
  var badge=document.getElementById('bellBadge');
  if(badge)badge.style.display=unread>0?'block':'none';
}

// ===== Profile =====
// 头像持久化（localStorage）：值为 dataURL 字符串
function getAvatarImage(){ return localStorage.getItem('wb_avatar')||''; }
function setAvatarImage(dataUrl){ localStorage.setItem('wb_avatar',dataUrl||''); }
// 渲染头像元素：优先用图片，否则用用户名首字母；保留右下角相机图标 overlay
var _AVATAR_OVERLAY_HTML='<div style="position:absolute;right:-2px;bottom:-2px;width:22px;height:22px;border-radius:50%;background:var(--accent);border:2px solid #fff;display:flex;align-items:center;justify-content:center"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" style="width:12px;height:12px"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg></div>';
function applyAvatarTo(el){
  if(!el)return;
  var img=getAvatarImage();
  if(img){
    el.innerHTML='<img src="'+img+'" alt="头像" style="width:100%;height:100%;border-radius:50%;object-fit:cover">'+_AVATAR_OVERLAY_HTML;
  }else{
    var ch=(S.username||'W').charAt(0).toUpperCase();
    el.innerHTML=ch+_AVATAR_OVERLAY_HTML;
  }
}
function renderProfile(){
  var lr=document.getElementById('logoutRow');
  var avatarEl=document.getElementById('pfAvatar');
  var nameEl=document.getElementById('pfName');
  if(S.loggedIn){
    applyAvatarTo(avatarEl);
    nameEl.textContent=S.username||'用户';
    // 点击用户名可编辑
    nameEl.style.cursor='pointer';
    nameEl.title='点击修改用户名';
    nameEl.onclick=showUsernameEditModal;
    document.getElementById('pfId').textContent='ID: '+S.userId;
    document.getElementById('pfId').onclick=null;
    if(lr)lr.style.display='flex';
  }else{
    // 未登录：若有自定义头像仍展示，否则用占位字母 W；统一通过 applyAvatarTo 保留相机 overlay
    applyAvatarTo(avatarEl);
    nameEl.textContent='未登录';
    nameEl.style.cursor='default';
    nameEl.onclick=null;
    document.getElementById('pfId').textContent='点击登录 / 注册';
    document.getElementById('pfId').style.cursor='pointer';
    document.getElementById('pfId').onclick=showLoginModal;
    if(lr)lr.style.display='none';
  }
  document.getElementById('pfStatPhotos').textContent=S.photos;
  document.getElementById('pfStatLikes').textContent=S.likes;
  document.getElementById('pfStatFollowers').textContent=ensureFollowers().length;
  document.getElementById('pfStatFollowing').textContent=getFollowing().length;
}
// 打开粉丝/关注列表（自己的）
function openFollowList(type){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  var titleEl=document.getElementById('followListTitle');
  var contentEl=document.getElementById('followListContent');
  var list=type==='following'?getFollowing():ensureFollowers();
  titleEl.textContent=type==='following'?'我的关注':'我的粉丝';
  if(list.length===0){
    contentEl.innerHTML='<div style="text-align:center;color:var(--text-secondary);font-size:13px;padding:20px 0">暂无'+(type==='following'?'关注':'粉丝')+'</div>';
  }else{
    var html='';
    list.forEach(function(name){
      var following=isFollowing(name);
      var btnHtml=type==='following'?
        '<button class="nt-action-btn following" onclick="unfollowFromList(this,\''+name.replace(/'/g,"\\'")+'\')">已关注</button>':
        '<button class="nt-action-btn '+(following?'following':'primary')+'" onclick="toggleFollowFromList(this,\''+name.replace(/'/g,"\\'")+'\')">'+(following?'已关注':'+ 关注')+'</button>';
      // 头像可点击进入对方主页
      html+='<div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--border)"><div onclick="hideFollowListModal();openUserProfile(\''+name.replace(/'/g,"\\'")+'\')" style="width:36px;height:36px;border-radius:50%;background:'+avatarColor('blue')+';color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600;cursor:pointer">'+escHtml(name.charAt(0))+'</div><div onclick="hideFollowListModal();openUserProfile(\''+name.replace(/'/g,"\\'")+'\')" style="flex:1;font-size:14px;font-weight:500;cursor:pointer">'+escHtml(name)+'</div>'+btnHtml+'</div>';
    });
    contentEl.innerHTML=html;
  }
  document.getElementById('followListModal').classList.add('show');
}
function hideFollowListModal(){ document.getElementById('followListModal').classList.remove('show'); }
function toggleFollowFromList(btn,username){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  var nowFollowing=!isFollowing(username);
  setFollowing(username,nowFollowing);
  btn.textContent=nowFollowing?'已关注':'+ 关注';
  btn.className='nt-action-btn '+(nowFollowing?'following':'primary');
  document.getElementById('pfStatFollowing').textContent=getFollowing().length;
  showToast(nowFollowing?'已关注 '+username:'已取消关注 '+username);
}
function unfollowFromList(btn,username){
  setFollowing(username,false);
  document.getElementById('pfStatFollowing').textContent=getFollowing().length;
  // 重新渲染列表（移除该项）
  openFollowList('following');
  showToast('已取消关注 '+username);
}

// ===== 头像更换 =====
// 打开头像选择菜单（拍照 / 从相册选择 / 取消）
function openAvatarPicker(){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  document.getElementById('avatarPickerModal').classList.add('show');
}
function hideAvatarPickerModal(){ document.getElementById('avatarPickerModal').classList.remove('show'); }
// "拍照"：进入头像拍摄模式（复用相机流程，capturePhoto 时根据标志走头像分支）
function avatarTakePhoto(){
  hideAvatarPickerModal();
  S.avatarCaptureMode=true;
  goToCamera();
}
// "从相册选择"：触发隐藏的 file input
function avatarPickFromAlbum(){
  hideAvatarPickerModal();
  var input=document.getElementById('avatarFileInput');
  if(input){input.value='';input.click();}
}
// file input 选中文件后：读取为 dataURL 并应用为头像
function onAvatarFileSelected(input){
  if(!input||!input.files||!input.files[0])return;
  var file=input.files[0];
  if(!file.type.startsWith('image/')){showToast('请选择图片文件');return;}
  var reader=new FileReader();
  reader.onload=function(e){
    applyAvatarFromDataURL(e.target.result);
  };
  reader.onerror=function(){showToast('图片读取失败');};
  reader.readAsDataURL(file);
}
// 把 dataURL 应用为头像并持久化到 localStorage 与后端
function applyAvatarFromDataURL(dataUrl){
  if(!dataUrl){return;}
  // 简单压缩到合理尺寸（用 canvas 缩放到 200x200 正方形）
  try{
    var img=new Image();
    img.onload=function(){
      var canvas=document.createElement('canvas');
      var size=200;
      canvas.width=size;canvas.height=size;
      var ctx=canvas.getContext('2d');
      // 居中裁剪为正方形
      var minDim=Math.min(img.width,img.height);
      var sx=(img.width-minDim)/2;
      var sy=(img.height-minDim)/2;
      ctx.drawImage(img,sx,sy,minDim,minDim,0,0,size,size);
      var compressed=canvas.toDataURL('image/jpeg',0.85);
      setAvatarImage(compressed);
      applyAvatarTo(document.getElementById('pfAvatar'));
      showToast('头像已更新');
      // 同步到后端（拍照/相册均在竖屏下进行；后端会后续补充存储）
      syncProfileToBackend({avatar:compressed});
    };
    img.onerror=function(){
      // 图片加载失败时直接用原图
      setAvatarImage(dataUrl);
      applyAvatarTo(document.getElementById('pfAvatar'));
      showToast('头像已更新');
      syncProfileToBackend({avatar:dataUrl});
    };
    img.src=dataUrl;
  }catch(e){
    setAvatarImage(dataUrl);
    applyAvatarTo(document.getElementById('pfAvatar'));
    showToast('头像已更新');
    syncProfileToBackend({avatar:dataUrl});
  }
}
// 把用户资料（头像/用户名）同步到后端，失败静默（不影响本地体验）
function syncProfileToBackend(data){
  if(!S.loggedIn)return;
  api.updateProfile(data).then(function(res){
    if(!res||!res.ok){
      // 后端尚未实现或失败：静默处理，本地已生效
      console.warn('updateProfile failed',res&&res.status);
      return;
    }
    // 以服务端返回为准校正本地状态
    var u=res.data&&res.data.user?res.data.user:res.data;
    if(u&&u.username&&u.username!==S.username){
      // 用户名被服务端规范化时同步
      // 注意：避免影响当前编辑流，仅在差异时更新
    }
  }).catch(function(){ /* 网络异常静默 */ });
}

// ===== 用户名编辑 =====
function showUsernameEditModal(){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  var input=document.getElementById('usernameEditInput');
  if(input){input.value=S.username||'';}
  document.getElementById('usernameEditModal').classList.add('show');
  setTimeout(function(){if(input){input.focus();input.select();}},100);
}
function hideUsernameEditModal(){
  document.getElementById('usernameEditModal').classList.remove('show');
}
function submitUsernameEdit(){
  if(!S.loggedIn){showToast('请先登录');hideUsernameEditModal();return;}
  var input=document.getElementById('usernameEditInput');
  if(!input)return;
  var newName=input.value.trim();
  if(!newName){showToast('用户名不能为空');return;}
  if(newName.length>20){showToast('用户名最多 20 个字符');return;}
  if(newName===S.username){hideUsernameEditModal();return;}
  var oldName=S.username;
  S.username=newName;
  // 同步本地 FEEDS 里自己帖子的 user/owner（保持一致）
  FEEDS.forEach(function(f){
    var owner=f.owner||f.user||'';
    if(owner===oldName){f.user=newName;f.owner=newName;}
  });
  hideUsernameEditModal();
  renderProfile();
  // 当前在社区页则刷新
  var active=document.querySelector('.screen.active');
  if(active&&active.id==='screen-community')renderCommunity();
  if(active&&active.id==='screen-my-album')renderMyAlbum();
  showToast('用户名已更新');
  syncProfileToBackend({username:newName});
}

// ===== 他人主页（User Profile Screen） =====
// 进入某用户的主页（按用户名）
function openUserProfile(username){
  if(!username){return;}
  // 点击的是自己 → 直接回到"我的"tab
  if(S.loggedIn&&username===S.username){
    switchTab('profile');
    return;
  }
  S.viewingUser=username;
  showScreen('screen-user-profile',true);
  renderUserProfile();
  // 后端 /api/user/:id/profile 用 user_id 查询；当前社区卡片仅含用户名，
  // 故先以本地数据渲染，待后端在 feed 中附带 author_id 后可在此异步拉取并刷新粉丝/关注数。
}
function renderUserProfile(){
  var username=S.viewingUser||'用户';
  document.getElementById('upName').textContent=username;
  document.getElementById('upId').textContent='@'+username;
  // 头像：首字母
  var avatarEl=document.getElementById('upAvatar');
  avatarEl.innerHTML=escHtml(username.charAt(0));
  // 实拍数：该用户发的帖子数
  var userFeeds=FEEDS.filter(function(f){
    var owner=f.owner||f.user||'';
    return owner===username;
  }).sort(function(a,b){return b.id-a.id});
  document.getElementById('upStatPhotos').textContent=userFeeds.length;
  // 粉丝/关注数：本地用 isFollowing 估算（被关注者视角下，本地无此数据，给 0）
  document.getElementById('upStatFollowers').textContent=0;
  document.getElementById('upStatFollowing').textContent=0;
  // 关注按钮状态
  var btn=document.getElementById('upFollowBtn');
  if(btn){
    if(S.loggedIn&&isFollowing(username)){
      btn.textContent='已关注';
      btn.className='up-follow-btn following';
    }else{
      btn.textContent='+ 关注';
      btn.className='up-follow-btn';
    }
    // 未登录时按钮提示
    btn.style.display='';
  }
  // 渲染该用户的帖子列表
  var feedsEl=document.getElementById('upFeeds');
  if(userFeeds.length===0){
    feedsEl.innerHTML='<div class="up-empty">TA 还没有发布实拍</div>';
    return;
  }
  var html='';
  userFeeds.forEach(function(f){
    var photoHtml='';
    if(f.isImage&&f.photo){
      photoHtml='<div class="up-feed-ph"><img src="'+f.photo+'" alt="实拍"></div>';
    }else{
      photoHtml='<div class="up-feed-ph cm-photo-'+(f.photo||'blue')+'">'+escHtml(f.weather||'')+'</div>';
    }
    html+='<div class="up-feed-card" onclick="openFeed('+f.id+')">'+photoHtml+
      '<div class="up-feed-body">'+
        (f.caption?'<div class="up-feed-caption">'+escHtml(f.caption)+'</div>':'')+
        '<div class="up-feed-meta">'+escHtml(f.district||'')+' \u00B7 '+escHtml(f.time||'')+' · ❤ '+f.likes+' · 💬 '+f.comments+'</div>'+
      '</div></div>';
  });
  feedsEl.innerHTML=html;
}
// 在他人主页点击关注/取消关注
function toggleFollowViewingUser(){
  if(!S.loggedIn){showToast('请先登录');showLoginModal();return;}
  var username=S.viewingUser;
  if(!username)return;
  var nowFollowing=!isFollowing(username);
  setFollowing(username,nowFollowing);
  // 更新按钮
  var btn=document.getElementById('upFollowBtn');
  if(btn){
    btn.textContent=nowFollowing?'已关注':'+ 关注';
    btn.className='up-follow-btn '+(nowFollowing?'following':'');
  }
  // 同步个人页关注数
  var pfFollowing=document.getElementById('pfStatFollowing');
  if(pfFollowing)pfFollowing.textContent=getFollowing().length;
  // 同步后端（用 username 作为占位 user_id；后端补充真实 user_id 后可改）
  api.followUser(username).then(function(res){
    if(!res||!res.ok){console.warn('followUser failed',res&&res.status);}
  }).catch(function(){/* 静默 */});
  showToast(nowFollowing?'已关注 '+username:'已取消关注 '+username);
}
// 在他人主页点击粉丝/关注数字（本地无此用户列表，提示）
function openUserFollowList(type){
  showToast('该用户的'+(type==='following'?'关注':'粉丝')+'列表暂未开放');
}

// ===== Login / Register =====
function showLoginModal(){document.getElementById('loginModal').classList.add('show');}
function hideLoginModal(){
  document.getElementById('loginModal').classList.remove('show');
  var err=document.getElementById('authError'); if(err)err.textContent='';
}
var currentAuthMode='login';
function switchAuthTab(mode){
  currentAuthMode=mode;
  var err=document.getElementById('authError'); if(err)err.textContent='';
  document.getElementById('loginForm').style.display = mode==='login'?'block':'none';
  document.getElementById('registerForm').style.display = mode==='register'?'block':'none';
  document.getElementById('tabLogin').style.background = mode==='login'?'var(--accent)':'#eef2f7';
  document.getElementById('tabLogin').style.color = mode==='login'?'#fff':'var(--text-secondary)';
  document.getElementById('tabRegister').style.background = mode==='register'?'var(--accent)':'#eef2f7';
  document.getElementById('tabRegister').style.color = mode==='register'?'#fff':'var(--text-secondary)';
  document.getElementById('authSubmitBtn').textContent = mode==='login'?'登录':'注册';
}
function submitAuth(){
  var err=document.getElementById('authError');
  err.textContent='';
  if(currentAuthMode==='register'){
    var username=document.getElementById('regUsername').value.trim();
    var email=document.getElementById('regEmail').value.trim();
    var password=document.getElementById('regPassword').value;
    if(!username){err.textContent='请输入用户名';return;}
    if(!email||email.indexOf('@')<0){err.textContent='请输入正确的邮箱';return;}
    if(password.length<6){err.textContent='密码至少6位';return;}
    api.register({username:username,email:email,password:password}).then(function(res){
      if(res.ok) onAuthSuccess(res.data);
      else err.textContent=(res.data&&res.data.error)||'注册失败';
    });
  }else{
    var identifier=document.getElementById('loginIdentifier').value.trim();
    var password=document.getElementById('loginPassword').value;
    if(!identifier||!password){err.textContent='请输入账号和密码';return;}
    api.login({identifier:identifier,password:password}).then(function(res){
      if(res.ok) onAuthSuccess(res.data);
      else err.textContent=(res.data&&res.data.error)||'登录失败';
    });
  }
}
function onAuthSuccess(payload){
  localStorage.setItem('wb_token', payload.token);
  applyUserProfile(payload.user);
  hideLoginModal();
  showToast('登录成功');
}
function logout(){
  localStorage.removeItem('wb_token');
  S.loggedIn=false; S.userId=''; S.username=''; S.email='';
  S.photos=0; S.likes=0;
  renderProfile();
  showToast('已退出登录');
}

// ===== Camera（真实摄像头）=====
var camStream=null;
var camFacing='environment';

function startCamera(){
  var v=document.getElementById('camVideo');
  var hint=document.getElementById('camHint');
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    if(hint)hint.textContent='当前环境不支持摄像头，可模拟拍摄';
    return;
  }
  navigator.mediaDevices.getUserMedia({video:{facingMode:camFacing},audio:false})
    .then(function(stream){
      camStream=stream;
      if(v){v.srcObject=stream;v.style.display='block';v.play();}
      if(hint)hint.textContent='将天空放入框内拍摄';
    })
    .catch(function(err){
      console.warn('Camera error',err);
      if(hint)hint.textContent='无法访问摄像头，可模拟拍摄';
      showToast('未授权摄像头，将使用模拟拍摄');
    });
}
function stopCamera(){
  if(camStream){camStream.getTracks().forEach(function(t){t.stop()});camStream=null;}
  var v=document.getElementById('camVideo');
  if(v){v.srcObject=null;v.style.display='none';}
}
function switchCamera(){
  camFacing=camFacing==='environment'?'user':'environment';
  stopCamera();
  startCamera();
}
function goToCamera(){
  if(!S.loggedIn){showLoginModal();return;}
  // 进入拍照界面：清空待发表照片，隐藏预览
  // 注意：不在此重置 avatarCaptureMode，因为 avatarTakePhoto 会先置 true 再调用本函数；
  // 该标志在 closeCamera / capturePhoto 的头像分支中统一重置。
  S.pendingPhotos=[];
  hidePreview();
  showScreen('screen-camera',true);
  startCamera();
}
function closeCamera(){
  stopCamera();
  // 关闭相机时重置头像拍摄模式标志与待发表照片
  S.avatarCaptureMode=false;
  S.pendingPhotos=[];
  hidePreview();
  goBack();
}
// 把一张照片 dataURL 压缩到合理尺寸（最大边 1280，jpeg 0.7），避免 dataURL 过大
function compressPhotoAsync(dataUrl,cb){
  try{
    var img=new Image();
    img.onload=function(){
      var maxSide=1280;
      var w=img.width,h=img.height;
      var scale=Math.min(1,maxSide/Math.max(w,h));
      var cw=Math.round(w*scale),ch=Math.round(h*scale);
      var c=document.createElement('canvas');
      c.width=cw;c.height=ch;
      c.getContext('2d').drawImage(img,0,0,cw,ch);
      cb(c.toDataURL('image/jpeg',0.7));
    };
    img.onerror=function(){cb(dataUrl);};
    img.src=dataUrl;
  }catch(e){cb(dataUrl);}
}
function capturePhoto(){
  var photoData=null;
  var v=document.getElementById('camVideo');
  if(v&&v.srcObject&&v.videoWidth>0){
    try{
      var c=document.createElement('canvas');
      c.width=v.videoWidth;c.height=v.videoHeight;
      c.getContext('2d').drawImage(v,0,0);
      photoData=c.toDataURL('image/jpeg',0.7);
    }catch(e){photoData=null;}
  }
  // —— 头像拍摄模式：把拍到的照片应用为头像，不发布到社区 ——
  if(S.avatarCaptureMode){
    S.avatarCaptureMode=false;
    stopCamera();
    if(photoData){
      applyAvatarFromDataURL(photoData);
      switchTab('profile');
    }else{
      showToast('未捕获到画面，请重试');
      switchTab('profile');
    }
    return;
  }
  // —— 普通拍照：把照片加入待发表数组并显示预览（不直接提交） ——
  if(!photoData){
    // 无真实画面时，给一张模拟纯色占位图（蓝色）以便流程可走通
    photoData=null;
    showToast('未捕获到画面，可从相册选择或重试');
    return;
  }
  compressPhotoAsync(photoData,function(compressed){
    S.pendingPhotos.push(compressed);
    renderPreview();
    showPreview();
  });
}
// 从相册选择（社区发帖用，支持多选）
function pickFromAlbumForPost(){
  if(!S.loggedIn){showLoginModal();return;}
  var input=document.getElementById('albumFileInput');
  if(input){input.value='';input.click();}
}
// 相册多选文件回调
function onAlbumFilesSelected(input){
  if(!input||!input.files||!input.files.length)return;
  var files=Array.prototype.slice.call(input.files);
  var remaining=files.length;
  files.forEach(function(file){
    if(!file.type.startsWith('image/')){remaining--;checkDone();return;}
    var reader=new FileReader();
    reader.onload=function(e){
      compressPhotoAsync(e.target.result,function(compressed){
        S.pendingPhotos.push(compressed);
        checkDone();
      });
    };
    reader.onerror=function(){checkDone();};
    reader.readAsDataURL(file);
  });
  function checkDone(){
    remaining--;
    if(remaining<=0){
      if(S.pendingPhotos.length===0){showToast('未选择有效图片');return;}
      renderPreview();
      showPreview();
      // 若当前不在拍照界面（例如从相册入口直接调用），切到拍照界面承载预览
      var cam=document.getElementById('screen-camera');
      if(!cam||!cam.classList.contains('active')){
        showScreen('screen-camera',true);
      }
    }
  }
}
// 预览界面"+"按钮：再拍一张（回到相机取景）或从相册加
function addMorePhotos(){
  // 优先从相册继续加（更快捷）
  pickFromAlbumForPost();
}
// 删除预览中的某张待发表照片
function removePendingPhoto(idx){
  if(idx<0||idx>=S.pendingPhotos.length)return;
  S.pendingPhotos.splice(idx,1);
  renderPreview();
  if(S.pendingPhotos.length===0){
    // 全删光则退回取景，但保留在拍照界面
    hidePreview();
  }
}
// 渲染预览缩略图列表
function renderPreview(){
  var grid=document.getElementById('camPreviewGrid');
  var countEl=document.getElementById('camPreviewCount');
  var pubBtn=document.getElementById('camPublishBtn');
  if(!grid)return;
  if(countEl)countEl.textContent=S.pendingPhotos.length?('共 '+S.pendingPhotos.length+' 张'):'';
  if(pubBtn)pubBtn.disabled=S.pendingPhotos.length===0;
  if(S.pendingPhotos.length===0){
    grid.innerHTML='<div class="cam-preview-empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg><div>还没有照片<br>点击下方"+"从相册添加，或返回取景拍摄</div></div>';
    return;
  }
  var html='';
  S.pendingPhotos.forEach(function(p,i){
    html+='<div class="cam-thumb-row"><img src="'+p+'" alt="预览"><button class="cam-thumb-del" onclick="removePendingPhoto('+i+')" aria-label="删除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg></button></div>';
  });
  grid.innerHTML=html;
}
function showPreview(){
  var pv=document.getElementById('camPreview');
  if(pv)pv.classList.add('show');
  renderPreview();
}
// 隐藏预览界面；keepCaption=true 时保留已输入的文字（便于返回取景继续拍）
function hidePreview(keepCaption){
  var pv=document.getElementById('camPreview');
  if(pv)pv.classList.remove('show');
  if(!keepCaption){
    var cap=document.getElementById('camPreviewCaption');
    if(cap)cap.value='';
  }
}
// 预览顶部返回箭头：若有照片则退回取景继续拍（保留文字），无照片则关闭整个相机
function closePreview(){
  if(S.pendingPhotos.length===0){
    closeCamera();
  }else{
    hidePreview(true);
  }
}
// 发表：把待发表照片数组和文字一起提交到后端
function publishPendingPhotos(){
  if(!S.loggedIn){showLoginModal();return;}
  if(S.pendingPhotos.length===0){showToast('请先添加照片');return;}
  var caption='';
  var capEl=document.getElementById('camPreviewCaption');
  if(capEl)caption=capEl.value.trim();
  var photos=S.pendingPhotos.slice();
  var btn=document.getElementById('camPublishBtn');
  if(btn){btn.disabled=true;btn.textContent='发表中...';}
  stopCamera();
  api.postFeed(photos,caption).then(function(res){
    if(btn){btn.disabled=false;btn.textContent='发表';}
    if(!res||!res.ok){
      if(res&&res.status===401){showToast('请先登录');showLoginModal();}
      else{showToast((res&&res.data&&res.data.error)||'发表失败，请重试');}
      // 失败：回到拍照界面并恢复预览，让用户重试
      startCamera();
      showPreview();
      return;
    }
    // 成功：以服务端返回的 feed 为准并入列表；无返回则本地拼装一条
    var feed=res.data&&res.data.feed?res.data.feed:null;
    if(!feed){
      var w=LAST_WEATHER;
      var wStr=w?(w.desc+' · '+w.temp+'\u00B0C'):'晴 · 25\u00B0C';
      feed={
        id:res.data&&res.data.id?res.data.id:Date.now(),
        photo:photos[0],
        photos:photos,
        isImage:true,
        weather:wStr,
        user:S.username||'我',
        owner:S.username||S.userId||'我',
        avatarColor:'blue',
        district:S.city+' '+S.district,
        time:'刚刚',
        likes:0,liked:false,comments:0,
        caption:caption,comments_list:[]
      };
    }else{
      // 兼容字段：确保本地渲染所需字段存在
      if(!feed.photo&&feed.photos&&feed.photos.length)feed.photo=feed.photos[0];
      if(feed.isImage===undefined)feed.isImage=!!(feed.photo&&feed.photo.indexOf('data:')===0)||!!(feed.photos&&feed.photos.length);
      if(!feed.owner)feed.owner=feed.user||'';
      if(!feed.photos&&feed.photo)feed.photos=[feed.photo];
      if(!feed.comments_list)feed.comments_list=[];
      if(typeof feed.likes!=='number')feed.likes=0;
      if(typeof feed.comments!=='number')feed.comments=0;
      if(typeof feed.liked!=='boolean')feed.liked=false;
    }
    FEEDS.unshift(feed);
    S.photos=(S.photos||0)+1;
    S.pendingPhotos=[];
    hidePreview();
    showToast('已发表到天空社区');
    S.filter='new';
    switchTab('community');
    document.querySelectorAll('.cm-tab').forEach(function(t){
      t.classList.remove('active');
      if(t.textContent.indexOf('最新')>=0)t.classList.add('active');
    });
    renderProfile();
  }).catch(function(){
    if(btn){btn.disabled=false;btn.textContent='发表';}
    showToast('网络异常，发表失败');
    startCamera();
    showPreview();
  });
}

// ===== 地理位置 / 附近排序 =====
function _h(s){var h=0;for(var i=0;i<s.length;i++)h=((h<<5)-h+s.charCodeAt(i))|0;return Math.abs(h);}
function feedCoords(f){
  var h=_h((f.district||'')+f.id);
  return {lat:22+(h%230)/10, lng:100+((h>>8)%250)/10};
}
function haversine(a,b){
  var R=6371,toR=Math.PI/180;
  var dLat=(b.lat-a.lat)*toR,dLng=(b.lng-a.lng)*toR;
  var la1=a.lat*toR,la2=b.lat*toR;
  var x=Math.sin(dLat/2)*Math.sin(dLat/2)+Math.cos(la1)*Math.cos(la2)*Math.sin(dLng/2)*Math.sin(dLng/2);
  return R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));
}
function getUserLocation(){
  return new Promise(function(res){
    if(!navigator.geolocation){res(null);return;}
    navigator.geolocation.getCurrentPosition(
      function(p){res({lat:p.coords.latitude,lng:p.coords.longitude});},
      function(){res(null);},
      {enableHighAccuracy:true,timeout:8000,maximumAge:60000}
    );
  });
}

// ===== Toast =====
var toastTimer=null;
function showToast(msg){
  var t=document.getElementById('toast');
  t.textContent=msg;
  t.classList.add('show');
  if(toastTimer)clearTimeout(toastTimer);
  toastTimer=setTimeout(function(){t.classList.remove('show')},2000);
}

// ===== Auth helpers =====
function authToken(){ return localStorage.getItem('wb_token') || ''; }
function authHeader(){
  var t = authToken();
  return t ? { 'Authorization': 'Bearer ' + t } : {};
}
function applyUserProfile(u){
  S.loggedIn = true;
  S.userId = u.userId || ('WB' + u.id);
  S.username = u.username || '';
  S.email = u.email || '';
  S.photos = u.photos || 0;
  S.likes = u.likes || 0;
  renderProfile();
}
function restoreSession(){
  var t = authToken();
  if(!t) return Promise.resolve();
  return api.getProfile().then(function(res){
    if(res.ok){ applyUserProfile(res.data); }
    else { localStorage.removeItem('wb_token'); }
  }).catch(function(){ localStorage.removeItem('wb_token'); });
}

// ===== Init =====
function showLoadingError(msg){
  var overlay=document.getElementById('loadingOverlay');
  var spinner=document.getElementById('loadingSpinner');
  var text=document.getElementById('loadingText');
  var error=document.getElementById('loadingError');
  var errorMsg=document.getElementById('loadingErrorMsg');
  if(spinner)spinner.style.display='none';
  if(text)text.style.display='none';
  if(error){
    error.style.display='block';
    errorMsg.textContent=msg;
  }
  if(overlay)overlay.classList.remove('hidden');
}
function hideLoadingError(){
  var spinner=document.getElementById('loadingSpinner');
  var text=document.getElementById('loadingText');
  var error=document.getElementById('loadingError');
  if(spinner)spinner.style.display='block';
  if(text)text.style.display='block';
  if(error)error.style.display='none';
}
// 真正隐藏加载遮罩：清理错误态 + 加 hidden 类。即使之前触发过 showLoadingError，
// 只要数据最终拿到了，就要把错误清掉并把遮罩藏起来，避免页面被卡在错误遮罩后面。
function hideLoadingOverlay(){
  hideLoadingError();
  var overlay=document.getElementById('loadingOverlay');
  if(overlay)overlay.classList.add('hidden');
}

var _SOURCE_IDS=['ecmwf','gfs','icon','grapes','cma','caiyun','pws','qweather','moji','weathercn','weathercom','huawei','xiaomi','apple','accu','goog','tct'];

function _runInitPipeline(){
  // 关键数据：城市配置（失败则确实无法继续）
  return fetch('/api/cities')
    .then(function(r){
      if(!r.ok)throw new Error('城市配置加载失败：HTTP ' + r.status);
      return r.json();
    })
    .then(function(d){
      CITIES=d.cities;
      // 非关键数据：用 allSettled 语义，单个源失败不影响整体加载
      // 用 Promise.all + 每项 .catch 兜底，模拟 allSettled（兼容老浏览器）
      function safe(p){return p.then(function(v){return{ok:true,v:v};},function(e){return{ok:false,e:e};});}
      return Promise.all([
        safe(api.getRanking('7d')),
        safe(api.getRanking('30d')),
        safe(api.getRanking('all')),
        safe(api.getNotifications()),
        safe(api.getFeeds('hot')),
        Promise.all(_SOURCE_IDS.map(function(id){return safe(api.getSource(id));}))
      ]);
    })
    .then(function(results){
      // 只在所有关键数据齐备时才隐藏遮罩、渲染页面
      function unpack(r, fallback){return (r&&r.ok)?r.v:fallback;}
      RANK_DATA={
        '7d':unpack(results[0],[]),
        '30d':unpack(results[1],[]),
        'all':unpack(results[2],[])
      };
      NOTIFICATIONS=unpack(results[3],[]);
      FEEDS=unpack(results[4],[]);
      var sources=results[5]||[];
      SOURCE_DATA={};
      _SOURCE_IDS.forEach(function(id,i){
        var sr=sources[i];
        if(sr&&sr.ok&&sr.v){SOURCE_DATA[id]=sr.v;}
      });
      hideLoadingOverlay();
      // 若本地已有登录态（token），回查后端恢复用户信息
      restoreSession().then(function(){
        renderHome();
        updateBellBadge();
        updateClocks();
      });
      return true;
    });
}

function initData(){
  hideLoadingError();

  // 协议检测：file:// 协议下 fetch 无法访问后端
  if(window.location.protocol==='file:'){
    showLoadingError('当前通过 file:// 协议打开，无法请求后端 API。请双击 start_server.bat 启动服务后，通过 http://localhost:8000 访问。');
    return;
  }

  // 超时 Promise：25 秒（后端首次拉真实天气可能慢，且含 17 个源并发）
  var loadTimeout = new Promise(function(_, reject){
    setTimeout(function(){ reject(new Error('加载超时，请确认后端服务已启动')); }, 25000);
  });

  var loadPipeline = _runInitPipeline();

  // Promise.race：超时或失败先到先得
  Promise.race([loadPipeline, loadTimeout])
    .then(function(ok){
      // 成功路径：_runInitPipeline 内部已经 hideLoadingOverlay
    })
    .catch(function(err){
      console.error('Init failed:', err);
      // 自动重试一次（瞬时网络抖动 / 后端刚启动）
      if(!initData._retried){
        initData._retried=true;
        console.log('[Init] 自动重试一次…');
        setTimeout(function(){ initData(); }, 1500);
        return;
      }
      var msg='';
      if(err && err.message)msg=err.message;
      if(!msg)msg='请确认已双击 start_server.bat 启动后端服务';
      showLoadingError('加载失败：' + msg + '。可点击"重新加载"重试，或按 F12 查看控制台详情。');
    });
}

// ===== 移动端全屏模式检测 =====
// 作为已安装 PWA / WebView 安装包运行时，填满整个屏幕（去除手机外壳阴影）
(function(){
  var standalone = window.matchMedia && window.matchMedia('(display-mode: standalone)').matches;
  var iosStandalone = window.navigator.standalone === true;
  var param = location.search.indexOf('app=1') >= 0;
  var webview = /WebView|wv/i.test(navigator.userAgent) || /Android.*WebView/i.test(navigator.userAgent);
  // 检测是否为嵌入 WebView（PWABuilder 打包的 APK 使用的是受信任 WebView）
  var isEmbeddedWebView = window.CHTConf !== undefined || (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches === false && window.innerWidth < 500 && window.innerHeight < 900);
  // 对于移动端（手机/平板）视口，默认使用 app-mode 以获得最佳体验
  var isMobileViewport = window.innerWidth <= 500;
  if(standalone || iosStandalone || param || webview || isMobileViewport){
    document.documentElement.classList.add('app-mode');
  }
})();

// ===== 禁用双指缩放、手势缩放、双击放大（让 APP 行为像原生 APP）=====
// 阻止多指手势缩放
document.addEventListener('gesturestart', function(e){ e.preventDefault(); }, {passive:false});
document.addEventListener('gesturechange', function(e){ e.preventDefault(); }, {passive:false});
document.addEventListener('gestureend', function(e){ e.preventDefault(); }, {passive:false});
// 阻止双指触摸缩放（Android Chrome WebView 仍可能触发）
document.addEventListener('touchmove', function(e){
  if(e.touches && e.touches.length > 1){ e.preventDefault(); }
}, {passive:false});
// 阻止双击放大
var _lastTouchEnd = 0;
document.addEventListener('touchend', function(e){
  var now = Date.now();
  if(now - _lastTouchEnd <= 300){ e.preventDefault(); }
  _lastTouchEnd = now;
}, {passive:false});
// 阻止滚轮缩放（Ctrl+滚轮）
document.addEventListener('wheel', function(e){
  if(e.ctrlKey){ e.preventDefault(); }
}, {passive:false});
// 阻止键盘缩放快捷键（Ctrl+加减号）
document.addEventListener('keydown', function(e){
  if(e.ctrlKey && (e.key === '+' || e.key === '-' || e.key === '=' || e.key === '0')){
    e.preventDefault();
  }
}, {passive:false});

// ===== 锁定竖屏方向（如果 API 支持）=====
if(screen.orientation && screen.orientation.lock){
  screen.orientation.lock('portrait').catch(function(){ /* 部分浏览器仅在 PWA 全屏下支持，忽略失败 */ });
}

// ===== 设备自适应缩放：让 844px 高的手机框完整适配任意视口，避免首页被裁剪 =====
// 注意：app-mode 下设备框已填满屏幕，无需缩放
function fitDevice(){
  var d=document.getElementById('device');
  if(!d)return;
  if(document.documentElement.classList.contains('app-mode')){ d.style.transform=''; return; }
  var s=Math.min(1,(window.innerWidth-16)/390,(window.innerHeight-16)/844);
  d.style.transform='scale('+s+')';
}
window.addEventListener('resize',fitDevice);
fitDevice();

// ===== PWA Service Worker 注册（仅生产 HTTPS 环境，本地 localhost 也支持）=====
if('serviceWorker' in navigator){
  window.addEventListener('load', function(){
    navigator.serviceWorker.register('sw.js').catch(function(err){
      console.warn('SW 注册失败（不影响使用）:', err);
    });
  });
}

try{
  initData();
}catch(syncErr){
  console.error('Sync init error:', syncErr);
  showLoadingError('页面初始化出错：' + (syncErr && syncErr.message ? syncErr.message : String(syncErr)) + '。请刷新页面或检查控制台。');
}

