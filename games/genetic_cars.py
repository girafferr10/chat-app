def get_js():
    return r"""
function initGeneticCars(container) {
  var W = Math.min((container.clientWidth || 700) - 16, 700);
  var H = 300;
  var POP = 20;
  var MAX_FRAMES = 700;
  var generation = 1;
  var bestAllTime = 0;
  var bestDna = null;
  var simSpeed = 1;
  var running = false;
  var animId = null;
  var terrain = [];
  var population = [];
  var liveCars = [];
  var genFinished = false;
  var camX = 0;
  var spinAngle = 0;

  var statusDiv = document.createElement('div');
  statusDiv.style.cssText = 'text-align:center;padding:6px 0;font-size:13px;color:var(--text-secondary);font-weight:500;';
  container.appendChild(statusDiv);

  var canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  canvas.style.cssText = 'border-radius:8px;border:2px solid var(--border);display:block;margin:0 auto;cursor:default;';
  container.appendChild(canvas);
  var ctx = canvas.getContext('2d');

  var infoDiv = document.createElement('div');
  infoDiv.style.cssText = 'display:flex;gap:16px;justify-content:center;flex-wrap:wrap;padding:8px 0;font-size:12px;color:var(--text-muted);';
  container.appendChild(infoDiv);

  var btnRow = document.createElement('div');
  btnRow.style.cssText = 'display:flex;gap:8px;justify-content:center;margin-top:6px;flex-wrap:wrap;';
  container.appendChild(btnRow);

  function btn(label, cb) {
    var b = document.createElement('button');
    b.textContent = label;
    b.className = 'game-reset-btn';
    b.style.cssText = 'margin-top:0;padding:7px 16px;font-size:12px;';
    b.addEventListener('click', cb);
    btnRow.appendChild(b);
    return b;
  }

  function genTerrain() {
    var pts = [];
    var x = 0, y = H * 0.62;
    pts.push({x:0, y:y});
    pts.push({x:20, y:y});
    pts.push({x:60, y:y}); // long flat start
    x = 60;
    var seed = Math.random();
    while (x < 6000) {
      var step = 18 + Math.random() * 28;
      x += step;
      var delta = (Math.random() - 0.44) * 38;
      y = Math.max(H * 0.22, Math.min(H * 0.88, y + delta));
      pts.push({x:x, y:y});
    }
    return pts;
  }

  function terrainY(x) {
    if (x <= 0) return terrain[0] ? terrain[0].y : H * 0.62;
    for (var i = 0; i < terrain.length - 1; i++) {
      if (terrain[i].x <= x && terrain[i+1].x > x) {
        var t = (x - terrain[i].x) / (terrain[i+1].x - terrain[i].x);
        return terrain[i].y + t * (terrain[i+1].y - terrain[i].y);
      }
    }
    return terrain[terrain.length-1].y;
  }

  function terrainSlope(x) {
    for (var i = 0; i < terrain.length - 1; i++) {
      if (terrain[i].x <= x && terrain[i+1].x > x) {
        return Math.atan2(terrain[i+1].y - terrain[i].y, terrain[i+1].x - terrain[i].x);
      }
    }
    return 0;
  }

  function randDna() {
    return {
      wheelbase: 28 + Math.random() * 55,
      frontR: 7 + Math.random() * 22,
      rearR: 7 + Math.random() * 22,
      torque: 0.2 + Math.random() * 2.8,
      chassisH: 12 + Math.random() * 38,
      verts: Array.from({length:8}, function() { return 8 + Math.random() * 45; }),
      color: Math.floor(Math.random() * 360)
    };
  }

  function crossover(a, b) {
    return {
      wheelbase: Math.random() < 0.5 ? a.wheelbase : b.wheelbase,
      frontR: Math.random() < 0.5 ? a.frontR : b.frontR,
      rearR: Math.random() < 0.5 ? a.rearR : b.rearR,
      torque: Math.random() < 0.5 ? a.torque : b.torque,
      chassisH: Math.random() < 0.5 ? a.chassisH : b.chassisH,
      verts: a.verts.map(function(v, i) { return Math.random() < 0.5 ? v : b.verts[i]; }),
      color: Math.random() < 0.5 ? a.color : b.color
    };
  }

  function mutate(dna, rate) {
    function m(v, mn, mx) {
      if (Math.random() < rate) v = v * (0.65 + Math.random() * 0.7);
      return Math.max(mn, Math.min(mx || 9999, v));
    }
    return {
      wheelbase: m(dna.wheelbase, 20, 100),
      frontR: m(dna.frontR, 5, 35),
      rearR: m(dna.rearR, 5, 35),
      torque: m(dna.torque, 0.1, 4),
      chassisH: m(dna.chassisH, 8, 55),
      verts: dna.verts.map(function(v) { return m(v, 5, 60); }),
      color: Math.random() < rate ? Math.floor(Math.random() * 360) : dna.color
    };
  }

  function evalCar(dna) {
    var x = 60, vx = 0, maxX = x;
    var stuckCount = 0;
    for (var f = 0; f < MAX_FRAMES; f++) {
      var slope = terrainSlope(x + dna.wheelbase * 0.5);
      var cosS = Math.cos(slope), sinS = Math.sin(slope);
      var drive = dna.torque * cosS * cosS * (1 - Math.abs(sinS) * 0.5);
      var drag = 0.008 * dna.chassisH / 20;
      var accel = drive - drag * vx * vx - 0.005;
      vx = Math.max(0, vx + accel) * 0.978;
      if (Math.abs(slope) > 1.1) { vx *= 0.5; }
      if (Math.abs(slope) > 1.4) { break; }
      x += vx;
      if (x > maxX) { maxX = x; stuckCount = 0; }
      else stuckCount++;
      if (stuckCount > 120 && f > 60) break;
      if (vx < 0.02 && f > 80) break;
    }
    return maxX - 60;
  }

  function makeCar(dna) {
    return { dna: dna, x: 60, vx: 0, fitness: 0, alive: true, frame: 0, stuck: 0, lastX: 60 };
  }

  function stepCar(car) {
    if (!car.alive) return;
    var dna = car.dna;
    var slope = terrainSlope(car.x + dna.wheelbase * 0.5);
    var cosS = Math.cos(slope), sinS = Math.sin(slope);
    var drive = dna.torque * cosS * cosS * (1 - Math.abs(sinS) * 0.5);
    var drag = 0.008 * dna.chassisH / 20;
    var accel = drive - drag * car.vx * car.vx - 0.005;
    car.vx = Math.max(0, car.vx + accel) * 0.978;
    if (Math.abs(slope) > 1.1) car.vx *= 0.5;
    if (Math.abs(slope) > 1.4) { car.alive = false; return; }
    car.x += car.vx;
    if (car.x > car.fitness) { car.fitness = car.x; car.stuck = 0; }
    else car.stuck++;
    car.frame++;
    if (car.stuck > 150 && car.frame > 60) car.alive = false;
    if (car.vx < 0.02 && car.frame > 80) car.alive = false;
    if (car.frame >= MAX_FRAMES) car.alive = false;
  }

  function drawTerrain(camX) {
    ctx.save();
    ctx.strokeStyle = '#4a5568';
    ctx.lineWidth = 2;
    var first = true;
    ctx.beginPath();
    for (var i = 0; i < terrain.length; i++) {
      var sx = terrain[i].x - camX;
      var sy = terrain[i].y;
      if (sx < -30 || sx > W + 30) continue;
      if (first) { ctx.moveTo(sx, sy); first = false; }
      else ctx.lineTo(sx, sy);
    }
    if (!first) {
      ctx.lineTo(W + 40, H + 20);
      ctx.lineTo(-40, H + 20);
      ctx.closePath();
      var grad = ctx.createLinearGradient(0, H * 0.4, 0, H);
      grad.addColorStop(0, '#3d4a5c');
      grad.addColorStop(1, '#1a2233');
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawCarViz(car, camX, isBest) {
    var dna = car.dna;
    var sx = car.x - camX;
    if (!car.alive && !isBest) return;
    if (sx < -120 || sx > W + 120) return;

    var halfWB = dna.wheelbase * 0.5;
    var frontX = car.x + halfWB;
    var rearX = car.x - halfWB;
    var frontTY = terrainY(frontX);
    var rearTY = terrainY(rearX);
    var slope = Math.atan2(frontTY - rearTY, dna.wheelbase);
    var frontWY = frontTY - dna.frontR;
    var rearWY = rearTY - dna.rearR;
    var bodyY = (frontWY + rearWY) / 2 - dna.chassisH * 0.3;

    var alpha = car.alive ? 1 : 0.25;
    var hue = dna.color;
    var sat = isBest ? 80 : 60;
    var lit = isBest ? 55 : 45;

    ctx.save();
    ctx.globalAlpha = alpha;

    // Draw line from body to each wheel
    ctx.strokeStyle = 'hsl(' + hue + ',' + sat + '%,' + (lit - 10) + '%)';
    ctx.lineWidth = isBest ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(frontX - camX, frontWY);
    ctx.lineTo(sx, bodyY);
    ctx.lineTo(rearX - camX, rearWY);
    ctx.stroke();

    // Chassis polygon
    ctx.save();
    ctx.translate(sx, bodyY);
    ctx.rotate(slope);
    var nv = dna.verts.length;
    ctx.beginPath();
    for (var i = 0; i < nv; i++) {
      var a = (i / nv) * Math.PI * 2 - Math.PI / 2;
      var r = dna.verts[i] * (dna.chassisH / 50);
      var px = Math.cos(a) * r;
      var py = Math.sin(a) * r * 0.55;
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = 'hsla(' + hue + ',' + sat + '%,' + lit + '%, 0.35)';
    ctx.strokeStyle = 'hsl(' + hue + ',' + sat + '%,' + (lit + 10) + '%)';
    ctx.lineWidth = isBest ? 2 : 1;
    ctx.fill(); ctx.stroke();
    ctx.restore();

    // Wheels
    function drawWheel(wx, wy, wr, spin) {
      var wsx = wx - camX;
      ctx.save();
      ctx.translate(wsx, wy);
      ctx.beginPath();
      ctx.arc(0, 0, wr, 0, Math.PI * 2);
      ctx.fillStyle = 'hsla(' + hue + ',' + sat + '%, 30%, 0.6)';
      ctx.strokeStyle = 'hsl(' + hue + ',' + sat + '%,' + (lit + 5) + '%)';
      ctx.lineWidth = isBest ? 2 : 1;
      ctx.fill(); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(Math.cos(spin) * wr * 0.75, Math.sin(spin) * wr * 0.75);
      ctx.strokeStyle = 'rgba(255,255,255,' + (isBest ? 0.7 : 0.35) + ')';
      ctx.lineWidth = isBest ? 2 : 1;
      ctx.stroke();
      ctx.restore();
    }

    var spin = car.x / (dna.frontR + 1);
    drawWheel(frontX, frontWY, dna.frontR, spin);
    drawWheel(rearX, rearWY, dna.rearR, spin * (dna.frontR / (dna.rearR + 1)));

    if (isBest && car.alive) {
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('\u2605', sx, bodyY - dna.chassisH * 0.5 - 8);
    }

    ctx.restore();
  }

  function evolve() {
    var sorted = population.slice().sort(function(a, b) { return b.fitness - a.fitness; });
    var topFit = sorted[0].fitness - 60;
    if (topFit > bestAllTime) {
      bestAllTime = topFit;
      bestDna = sorted[0].dna;
    }
    generation++;
    var newPop = [sorted[0].dna, sorted[1] ? sorted[1].dna : mutate(sorted[0].dna, 0.3)];
    var topN = Math.max(2, Math.floor(POP * 0.5));
    while (newPop.length < POP) {
      var ia = Math.floor(Math.random() * topN);
      var ib = Math.floor(Math.random() * topN);
      var child = crossover(sorted[ia].dna, sorted[ib].dna);
      child = mutate(child, 0.18);
      newPop.push(child);
    }
    population = newPop.map(function(d) { return makeCar(d); });
    genFinished = false;
  }

  function drawFrame() {
    // Sky
    var grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, '#0f1729');
    grad.addColorStop(1, '#1e2d45');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Stars (static)
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    var starRng = 42;
    for (var s = 0; s < 40; s++) {
      starRng = (starRng * 1103515245 + 12345) & 0x7fffffff;
      var sx2 = (starRng % W);
      starRng = (starRng * 1103515245 + 12345) & 0x7fffffff;
      var sy2 = (starRng % (H * 0.45));
      ctx.fillRect(sx2, sy2, 1, 1);
    }

    drawTerrain(camX);

    // Sort: dead first, alive last (alive on top)
    var sorted2 = population.slice().sort(function(a, b) {
      if (a.alive !== b.alive) return a.alive ? 1 : -1;
      return a.fitness - b.fitness;
    });
    var best2 = null;
    population.forEach(function(c) { if (c.alive && (!best2 || c.x > best2.x)) best2 = c; });
    sorted2.forEach(function(c) { if (c !== best2) drawCarViz(c, camX, false); });
    if (best2) drawCarViz(best2, camX, true);

    // Distance markers
    ctx.font = '10px monospace';
    ctx.fillStyle = 'rgba(255,255,255,0.25)';
    ctx.textAlign = 'left';
    for (var mx = 0; mx < 6000; mx += 200) {
      var markerSx = mx - camX;
      if (markerSx > 10 && markerSx < W - 10) {
        ctx.fillText((mx) + 'm', markerSx, H - 8);
        ctx.fillStyle = 'rgba(255,255,255,0.1)';
        ctx.fillRect(markerSx, H * 0.25, 1, H * 0.6);
        ctx.fillStyle = 'rgba(255,255,255,0.25)';
      }
    }
  }

  var lastNow = 0;
  function loop(now) {
    if (!running) return;
    animId = requestAnimationFrame(loop);
    var dt = Math.min(32, now - lastNow);
    lastNow = now;

    // Run simulation steps
    var steps = simSpeed;
    for (var s = 0; s < steps; s++) {
      var alive = 0;
      population.forEach(function(car) {
        if (car.alive) { stepCar(car); alive++; }
      });
      if (alive === 0) { evolve(); break; }
    }

    // Camera follows best alive car
    var best = null;
    population.forEach(function(c) { if (c.alive && (!best || c.x > best.x)) best = c; });
    if (best) {
      var targetCam = Math.max(0, best.x - W * 0.35);
      camX += (targetCam - camX) * 0.05;
    }

    drawFrame();

    // Update status
    var alive2 = population.filter(function(c) { return c.alive; }).length;
    var topThis = population.reduce(function(a, b) { return b.fitness > a.fitness ? b : a; }, population[0]);
    var thisDist = Math.round(Math.max(0, (topThis ? topThis.fitness : 60) - 60));
    statusDiv.textContent = 'Gen ' + generation + '  |  Alive: ' + alive2 + '/' + POP + '  |  This gen: ' + thisDist + 'm  |  Best ever: ' + Math.round(bestAllTime) + 'm';

    // Info row
    if (best) {
      infoDiv.textContent = 'Torque: ' + best.dna.torque.toFixed(2) + '  Wheelbase: ' + best.dna.wheelbase.toFixed(0) + 'px  Front\u00D8: ' + (best.dna.frontR*2).toFixed(0) + 'px  Rear\u00D8: ' + (best.dna.rearR*2).toFixed(0) + 'px';
    }
  }

  function start() {
    if (animId) cancelAnimationFrame(animId);
    running = false;
    terrain = genTerrain();
    var initDna = Array.from({length: POP}, function() { return randDna(); });
    population = initDna.map(function(d) { return makeCar(d); });
    generation = 1; bestAllTime = 0; bestDna = null; camX = 0;
    running = true;
    lastNow = performance.now();
    animId = requestAnimationFrame(loop);
  }

  function stop() {
    running = false;
    if (animId) cancelAnimationFrame(animId);
    animId = null;
  }

  var speedBtn = btn('1x Speed', function() {
    if (simSpeed === 1) { simSpeed = 3; speedBtn.textContent = '3x Speed'; }
    else if (simSpeed === 3) { simSpeed = 8; speedBtn.textContent = '8x Speed'; }
    else { simSpeed = 1; speedBtn.textContent = '1x Speed'; }
  });

  btn('New Race', function() { start(); });
  btn('Stop', function() { stop(); statusDiv.textContent = 'Paused. Click New Race to restart.'; });
  btn('Resume', function() {
    if (!running) {
      running = true;
      lastNow = performance.now();
      animId = requestAnimationFrame(loop);
    }
  });

  // Handle container resize
  var resizeObs = null;
  if (typeof ResizeObserver !== 'undefined') {
    resizeObs = new ResizeObserver(function() {
      var nw = Math.min((container.clientWidth || 700) - 16, 700);
      if (nw !== W) { W = nw; canvas.width = W; }
    });
    resizeObs.observe(container);
  }

  start();
}
"""
