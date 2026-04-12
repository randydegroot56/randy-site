# Calendar Page — Design Spec
**Date:** 2026-04-06  
**Status:** Approved

---

## Summary

A personal calendar dashboard at `/calendar`, protected by Google OAuth, synced with a dedicated Google Calendar named **"RDG.dev"**. Full CRUD (create, read, update, delete) for events. Month and week views with a toggle. Consistent with the existing honey & smoke design system.

---

## Goals

- Personal-only dashboard (no public access)
- Google OAuth login (same Google account as the calendar)
- Dedicated Google Calendar "RDG.dev" — separate from personal agenda
- Full event management: view, create, edit, delete
- Month view + week view with toggle
- Compact event blocks; click to open detail panel with full info

---

## Non-Goals

- Public booking or availability page
- Multiple calendar support
- Notifications or reminders
- Mobile-native calendar sync (web only)

---

## Architecture

### Tech additions
- **NextAuth.js** (`next-auth`) — Google OAuth provider, session management, access token storage
- **Google Calendar API** — all event data reads/writes happen server-side via API routes

### File structure

```
src/
  app/
    calendar/
      page.js                        ← Protected calendar dashboard
    api/
      auth/
        [...nextauth]/
          route.js                   ← NextAuth handler (Google provider)
      calendar/
        events/
          route.js                   ← GET (list events) + POST (create event)
          [id]/
            route.js                 ← PATCH (update) + DELETE (delete)
  components/
    Calendar/
      CalendarGrid.jsx               ← Month view grid
      WeekView.jsx                   ← Week view with time slots
      CalendarHeader.jsx             ← Navigation + month/week toggle
      EventBlock.jsx                 ← Colored event block
      EventDetailPanel.jsx           ← Slide-in detail panel
      EventForm.jsx                  ← Create/edit modal form
.env.local                           ← Google credentials (gitignored)
```

---

## Authentication & Data Flow

### Google OAuth setup (one-time manual)
1. Create a Google Cloud project
2. Enable the Google Calendar API
3. Create OAuth 2.0 credentials (Client ID + Secret)
4. Add authorized redirect URI: `http://localhost:3000/api/auth/callback/google`
5. For production: add the production domain as an additional redirect URI

### Environment variables (`.env.local`)
```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXTAUTH_SECRET=          # random string, e.g. openssl rand -base64 32
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CALENDAR_ID=       # ID of the "RDG.dev" calendar (found in Google Calendar settings)
```

### Session flow
1. User visits `/calendar`
2. No session → automatic redirect to Google login
3. Post-login → redirect back to `/calendar`, JWT session stored
4. NextAuth stores the Google access token in the session
5. All Calendar API calls use this token server-side

### API routes
| Method | Path | Action |
|--------|------|--------|
| GET | `/api/calendar/events?month=YYYY-MM` | Fetch events for a given month |
| POST | `/api/calendar/events` | Create new event |
| PATCH | `/api/calendar/events/[id]` | Update existing event |
| DELETE | `/api/calendar/events/[id]` | Delete event |

All API routes verify session first — no session returns `401 Unauthorized`.

---

## UI Design

### Page layout
- Full viewport section, content in `maxWidth: 1100px` container
- `AnimateIn` for entrance animation
- `PageTransition` already applied via root layout

### CalendarHeader
- **Left:** previous / next navigation arrows
- **Center:** current period label (e.g. "April 2026") — `--font-heading`, `--text-2xl`
- **Right:** Month / Week toggle — gold underline on active (same pattern as Navbar `layoutId`)
- **Right:** "+ Event" button in `--accent-primary` gold

### CalendarGrid (month view)
- 7-column CSS grid
- Day headers (Ma Di Wo Do Vr Za Zo) in `--text-muted`, `--font-heading`
- Day cells with `--border-subtle` border
- Today's cell: highlighted with gold border (`--accent-primary`)
- Events: compact colored blocks — `--accent-primary` background, dark text, `--radius-sm`, single line (title + time)
- Overflow: "+N meer" label if more than ~3 events in a cell

### WeekView (week view)
- 7 columns (days) × time slots (00:00–24:00, 1hr rows)
- Events as vertical blocks positioned by start time, height = duration
- Same gold color style as month view
- Current time indicator: thin gold horizontal line

### EventDetailPanel
- Slides in from right (`AnimatePresence`, `x: 16 → 0`, `opacity: 0 → 1`)
- Glassmorphism card consistent with homepage GlassCard style
- Displays: title, date/time, description, location
- Action buttons: **Edit** (gold, `--accent-primary`) and **Delete** (subtle red `rgba(239,68,68,0.8)`)
- Close: X button or click outside

### EventForm (modal)
- Centered modal with `backdropFilter: blur(40px)` overlay
- Fields: title (required), date, start time, end time, description, location
- Buttons: **Save** (`--accent-primary`) and **Cancel** (ghost)
- Same glassmorphism style as homepage GlassCard

---

## Google Calendar — Dedicated "RDG.dev" Calendar

- Manually created in Google Calendar before setup
- Named "RDG.dev" for clear reference to the site
- Calendar ID saved in `.env.local` as `GOOGLE_CALENDAR_ID`
- All events created/read/updated/deleted exclusively in this calendar

---

## Error Handling

- Session expired → redirect to login
- Google Calendar API error → show inline error message in the UI (toast or inline text)
- Network failure → show retry option
- Form validation: title is required; end time must be after start time

---

## Out of Scope for v1

- Recurring events (creation — reading is fine)
- Drag-and-drop to move events
- Color picker per event
- Multiple calendar toggling
