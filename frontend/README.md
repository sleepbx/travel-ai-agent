# TravelAI Frontend

React + Vite frontend for TravelAI.

## What It Shows

- Home planner with flight, train, or bus transport selection
- Authenticated dashboard for saved trips
- Trip detail page with selected transport cards, hotel cards, day-wise itinerary, budget guardrails, and refinement prompts
- Travel HQ for rate refreshes, readiness tasks, and quick AI commands
- India Pulse cards with reliable travel images and live/search fallback results
- AI Nearby Planner / Instant Escape page for short local plans, hidden gems, food trails, rainy-day backups, social sharing, and structured itinerary JSON

## Transport UI

Users can choose:

```text
flight | train | bus
```

The selected mode is sent to the backend as:

```json
{
  "transport_mode": "train"
}
```

Trip cards display per-person fare and total fare separately. Flight rates are treated as per-person values, then multiplied by traveler count in the trip total.

## Environment

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For deployment, point it at the deployed backend:

```env
VITE_API_BASE_URL=https://your-backend-domain.com
```

## Commands

```powershell
npm install
npm run dev
npm run lint
npm run build
npm run preview
npm run start
```

If PowerShell blocks `npm.ps1`, use:

```powershell
npm.cmd run build
```

## Deployment Readiness

The latest check passed:

```text
npm.cmd run lint
npm.cmd run build
```

Vite writes the production bundle to `frontend/dist/`.

For static hosting, deploy `frontend/dist` and set:

```env
VITE_API_BASE_URL=https://your-backend-domain.com
```

For container-style hosts, `npm run start` runs Vite preview and respects the platform `PORT`.
