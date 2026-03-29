/**
 * AsteroidsGame — a classic Asteroids arcade game rendered on a canvas.
 *
 * The player controls a ship with arrow keys / WASD, shoots with Space,
 * and destroys asteroids for points. Large asteroids split into smaller ones.
 */
import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types & constants
// ---------------------------------------------------------------------------

const WIDTH = 640;
const HEIGHT = 480;
const SHIP_SIZE = 12;
const SHIP_THRUST = 0.12;
const SHIP_FRICTION = 0.985;
const SHIP_TURN_SPEED = 0.065;
const BULLET_SPEED = 6;
const BULLET_LIFE = 55;
const MAX_BULLETS = 8;
const ASTEROID_SPEED_RANGE = [0.5, 1.8] as const;
const INITIAL_ASTEROIDS = 4;
const ASTEROID_SIZES = [40, 22, 12] as const;
const ASTEROID_POINTS = [20, 50, 100] as const;

type Vec2 = { x: number; y: number };

type Ship = Vec2 & {
  angle: number;
  vx: number;
  vy: number;
  invincible: number; // frames remaining
};

type Bullet = Vec2 & { vx: number; vy: number; life: number };

type Asteroid = Vec2 & {
  vx: number;
  vy: number;
  radius: number;
  sizeIdx: number; // 0=large, 1=med, 2=small
  vertices: number[]; // jagged shape offsets
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function randomAsteroidVertices(): number[] {
  const count = 8 + Math.floor(Math.random() * 5);
  return Array.from({ length: count }, () => 0.7 + Math.random() * 0.6);
}

function spawnAsteroid(sizeIdx: number, x?: number, y?: number): Asteroid {
  const angle = Math.random() * Math.PI * 2;
  const speed =
    ASTEROID_SPEED_RANGE[0] +
    Math.random() * (ASTEROID_SPEED_RANGE[1] - ASTEROID_SPEED_RANGE[0]);
  return {
    x: x ?? Math.random() * WIDTH,
    y: y ?? Math.random() * HEIGHT,
    vx: Math.cos(angle) * speed * (1 + sizeIdx * 0.3),
    vy: Math.sin(angle) * speed * (1 + sizeIdx * 0.3),
    radius: ASTEROID_SIZES[sizeIdx],
    sizeIdx,
    vertices: randomAsteroidVertices(),
  };
}

function spawnWave(count: number): Asteroid[] {
  const asteroids: Asteroid[] = [];
  for (let i = 0; i < count; i++) {
    // Spawn away from center (where ship starts)
    let x: number, y: number;
    do {
      x = Math.random() * WIDTH;
      y = Math.random() * HEIGHT;
    } while (Math.hypot(x - WIDTH / 2, y - HEIGHT / 2) < 120);
    asteroids.push(spawnAsteroid(0, x, y));
  }
  return asteroids;
}

function wrap(pos: Vec2): Vec2 {
  let { x, y } = pos;
  if (x < 0) x += WIDTH;
  if (x > WIDTH) x -= WIDTH;
  if (y < 0) y += HEIGHT;
  if (y > HEIGHT) y -= HEIGHT;
  return { x, y };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export type AsteroidsGameProps = {
  onClose: () => void;
};

export default function AsteroidsGame({ onClose }: AsteroidsGameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const keysRef = useRef(new Set<string>());
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [gameOver, setGameOver] = useState(false);
  const [wave, setWave] = useState(1);
  const gameStateRef = useRef({
    ship: {
      x: WIDTH / 2,
      y: HEIGHT / 2,
      angle: -Math.PI / 2,
      vx: 0,
      vy: 0,
      invincible: 120,
    } as Ship,
    bullets: [] as Bullet[],
    asteroids: spawnWave(INITIAL_ASTEROIDS),
    score: 0,
    lives: 3,
    wave: 1,
    gameOver: false,
    particles: [] as { x: number; y: number; vx: number; vy: number; life: number }[],
  });

  const resetGame = useCallback(() => {
    const gs = gameStateRef.current;
    gs.ship = { x: WIDTH / 2, y: HEIGHT / 2, angle: -Math.PI / 2, vx: 0, vy: 0, invincible: 120 };
    gs.bullets = [];
    gs.asteroids = spawnWave(INITIAL_ASTEROIDS);
    gs.particles = [];
    gs.score = 0;
    gs.lives = 3;
    gs.wave = 1;
    gs.gameOver = false;
    setScore(0);
    setLives(3);
    setWave(1);
    setGameOver(false);
  }, []);

  // Auto-focus the canvas so keyboard input goes to the game immediately.
  useEffect(() => {
    canvasRef.current?.focus();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) {
        e.preventDefault();
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      keysRef.current.delete(e.key);
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    let shootCooldown = 0;
    let frameId: number;

    const tick = () => {
      const gs = gameStateRef.current;
      const keys = keysRef.current;

      if (!gs.gameOver) {
        // --- Ship controls ---
        const ship = gs.ship;
        if (keys.has("ArrowLeft") || keys.has("a")) ship.angle -= SHIP_TURN_SPEED;
        if (keys.has("ArrowRight") || keys.has("d")) ship.angle += SHIP_TURN_SPEED;
        if (keys.has("ArrowUp") || keys.has("w")) {
          ship.vx += Math.cos(ship.angle) * SHIP_THRUST;
          ship.vy += Math.sin(ship.angle) * SHIP_THRUST;
        }
        ship.vx *= SHIP_FRICTION;
        ship.vy *= SHIP_FRICTION;
        ship.x += ship.vx;
        ship.y += ship.vy;
        const wrapped = wrap(ship);
        ship.x = wrapped.x;
        ship.y = wrapped.y;
        if (ship.invincible > 0) ship.invincible--;

        // --- Shooting ---
        if (shootCooldown > 0) shootCooldown--;
        if ((keys.has(" ") || keys.has("Enter")) && shootCooldown === 0 && gs.bullets.length < MAX_BULLETS) {
          gs.bullets.push({
            x: ship.x + Math.cos(ship.angle) * SHIP_SIZE,
            y: ship.y + Math.sin(ship.angle) * SHIP_SIZE,
            vx: Math.cos(ship.angle) * BULLET_SPEED + ship.vx * 0.3,
            vy: Math.sin(ship.angle) * BULLET_SPEED + ship.vy * 0.3,
            life: BULLET_LIFE,
          });
          shootCooldown = 8;
        }

        // --- Update bullets ---
        gs.bullets = gs.bullets.filter((b) => {
          b.x += b.vx;
          b.y += b.vy;
          const w = wrap(b);
          b.x = w.x;
          b.y = w.y;
          b.life--;
          return b.life > 0;
        });

        // --- Update asteroids ---
        for (const a of gs.asteroids) {
          a.x += a.vx;
          a.y += a.vy;
          const w = wrap(a);
          a.x = w.x;
          a.y = w.y;
        }

        // --- Bullet-asteroid collisions ---
        const newAsteroids: Asteroid[] = [];
        gs.asteroids = gs.asteroids.filter((a) => {
          for (let bi = gs.bullets.length - 1; bi >= 0; bi--) {
            const b = gs.bullets[bi];
            if (Math.hypot(b.x - a.x, b.y - a.y) < a.radius) {
              gs.bullets.splice(bi, 1);
              gs.score += ASTEROID_POINTS[a.sizeIdx];
              setScore(gs.score);
              // Spawn particles
              for (let p = 0; p < 6; p++) {
                const pa = Math.random() * Math.PI * 2;
                const ps = 1 + Math.random() * 2;
                gs.particles.push({ x: a.x, y: a.y, vx: Math.cos(pa) * ps, vy: Math.sin(pa) * ps, life: 20 + Math.random() * 15 });
              }
              // Split
              if (a.sizeIdx < 2) {
                newAsteroids.push(spawnAsteroid(a.sizeIdx + 1, a.x, a.y));
                newAsteroids.push(spawnAsteroid(a.sizeIdx + 1, a.x, a.y));
              }
              return false;
            }
          }
          return true;
        });
        gs.asteroids.push(...newAsteroids);

        // --- Ship-asteroid collisions ---
        if (ship.invincible <= 0) {
          for (const a of gs.asteroids) {
            if (Math.hypot(ship.x - a.x, ship.y - a.y) < a.radius + SHIP_SIZE * 0.6) {
              gs.lives--;
              setLives(gs.lives);
              // Explosion particles
              for (let p = 0; p < 12; p++) {
                const pa = Math.random() * Math.PI * 2;
                const ps = 1 + Math.random() * 3;
                gs.particles.push({ x: ship.x, y: ship.y, vx: Math.cos(pa) * ps, vy: Math.sin(pa) * ps, life: 30 + Math.random() * 20 });
              }
              if (gs.lives <= 0) {
                gs.gameOver = true;
                setGameOver(true);
              } else {
                ship.x = WIDTH / 2;
                ship.y = HEIGHT / 2;
                ship.vx = 0;
                ship.vy = 0;
                ship.invincible = 120;
              }
              break;
            }
          }
        }

        // --- Next wave ---
        if (gs.asteroids.length === 0 && !gs.gameOver) {
          gs.wave++;
          setWave(gs.wave);
          gs.asteroids = spawnWave(INITIAL_ASTEROIDS + gs.wave - 1);
          gs.ship.invincible = 90;
        }
      }

      // --- Update particles ---
      gs.particles = gs.particles.filter((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.vx *= 0.97;
        p.vy *= 0.97;
        p.life--;
        return p.life > 0;
      });

      // --- Draw ---
      ctx.fillStyle = "#0a0a1a";
      ctx.fillRect(0, 0, WIDTH, HEIGHT);

      // Stars background (static)
      ctx.fillStyle = "rgba(255,255,255,0.3)";
      for (let i = 0; i < 60; i++) {
        // Deterministic stars from seed
        const sx = ((i * 7919 + 31) % WIDTH);
        const sy = ((i * 6271 + 17) % HEIGHT);
        ctx.fillRect(sx, sy, 1, 1);
      }

      // Particles
      for (const p of gs.particles) {
        const alpha = Math.min(1, p.life / 15);
        ctx.fillStyle = `rgba(255,${150 + Math.floor(Math.random() * 105)},50,${alpha})`;
        ctx.fillRect(p.x - 1, p.y - 1, 2, 2);
      }

      // Asteroids
      ctx.strokeStyle = "#8b9dc3";
      ctx.lineWidth = 1.5;
      for (const a of gs.asteroids) {
        ctx.beginPath();
        for (let i = 0; i <= a.vertices.length; i++) {
          const vi = i % a.vertices.length;
          const angle = (vi / a.vertices.length) * Math.PI * 2;
          const r = a.radius * a.vertices[vi];
          const px = a.x + Math.cos(angle) * r;
          const py = a.y + Math.sin(angle) * r;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.stroke();
      }

      // Ship
      if (!gs.gameOver) {
        const ship = gs.ship;
        const blink = ship.invincible > 0 && Math.floor(ship.invincible / 4) % 2 === 0;
        if (!blink) {
          ctx.save();
          ctx.translate(ship.x, ship.y);
          ctx.rotate(ship.angle);
          ctx.strokeStyle = "#60e0ff";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(SHIP_SIZE, 0);
          ctx.lineTo(-SHIP_SIZE * 0.7, -SHIP_SIZE * 0.6);
          ctx.lineTo(-SHIP_SIZE * 0.4, 0);
          ctx.lineTo(-SHIP_SIZE * 0.7, SHIP_SIZE * 0.6);
          ctx.closePath();
          ctx.stroke();

          // Thrust flame
          if (keys.has("ArrowUp") || keys.has("w")) {
            ctx.strokeStyle = "#ff8040";
            ctx.beginPath();
            ctx.moveTo(-SHIP_SIZE * 0.5, -SHIP_SIZE * 0.25);
            ctx.lineTo(-SHIP_SIZE * (0.8 + Math.random() * 0.4), 0);
            ctx.lineTo(-SHIP_SIZE * 0.5, SHIP_SIZE * 0.25);
            ctx.stroke();
          }
          ctx.restore();
        }
      }

      // Bullets
      ctx.fillStyle = "#ffffff";
      for (const b of gs.bullets) {
        ctx.beginPath();
        ctx.arc(b.x, b.y, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // HUD
      ctx.fillStyle = "#60e0ff";
      ctx.font = '16px "Press Start 2P", monospace';
      ctx.textAlign = "left";
      ctx.fillText(`SCORE ${gs.score}`, 12, 24);
      ctx.textAlign = "right";
      ctx.fillText(`WAVE ${gs.wave}`, WIDTH - 12, 24);
      ctx.textAlign = "center";
      // Lives
      for (let i = 0; i < gs.lives; i++) {
        const lx = WIDTH / 2 - (gs.lives - 1) * 12 + i * 24;
        ctx.save();
        ctx.translate(lx, 20);
        ctx.rotate(-Math.PI / 2);
        ctx.strokeStyle = "#60e0ff";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(7, 0);
        ctx.lineTo(-4, -4);
        ctx.lineTo(-2, 0);
        ctx.lineTo(-4, 4);
        ctx.closePath();
        ctx.stroke();
        ctx.restore();
      }

      if (gs.gameOver) {
        ctx.fillStyle = "rgba(0,0,0,0.6)";
        ctx.fillRect(0, HEIGHT / 2 - 50, WIDTH, 100);
        ctx.fillStyle = "#ff4060";
        ctx.font = '24px "Press Start 2P", monospace';
        ctx.textAlign = "center";
        ctx.fillText("GAME OVER", WIDTH / 2, HEIGHT / 2 - 10);
        ctx.fillStyle = "#8b9dc3";
        ctx.font = '12px "Press Start 2P", monospace';
        ctx.fillText("Press R to restart", WIDTH / 2, HEIGHT / 2 + 25);
      }

      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, []);

  // Restart on R key
  useEffect(() => {
    const handleRestart = (e: KeyboardEvent) => {
      if (e.key === "r" || e.key === "R") {
        if (gameStateRef.current.gameOver) {
          resetGame();
        }
      }
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleRestart);
    return () => window.removeEventListener("keydown", handleRestart);
  }, [onClose, resetGame]);

  return (
    <section className="card asteroids-card">
      <header className="asteroids-header">
        <h1>ASTEROIDS</h1>
        <div className="asteroids-stats">
          <span>Score: {score}</span>
          <span>Wave: {wave}</span>
          <span>Lives: {lives}</span>
        </div>
        <button
          type="button"
          className="asteroids-close-btn"
          onClick={onClose}
          aria-label="Close arcade"
        >
          &times;
        </button>
      </header>
      <div className="asteroids-canvas-wrap">
        <canvas
          ref={canvasRef}
          width={WIDTH}
          height={HEIGHT}
          className="asteroids-canvas"
          tabIndex={0}
        />
      </div>
      {gameOver && (
        <div className="asteroids-restart-row">
          <button type="button" className="asteroids-restart-btn" onClick={resetGame}>
            Play Again
          </button>
        </div>
      )}
      <p className="asteroids-controls">
        Arrow keys / WASD: move &middot; Space: shoot &middot; Esc: quit
      </p>
    </section>
  );
}
