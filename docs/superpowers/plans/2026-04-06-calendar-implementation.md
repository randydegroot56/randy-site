# Calendar Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal Google Calendar dashboard at `/calendar` with OAuth login, full CRUD, and month/week views — styled consistently with the honey & smoke design system.

**Architecture:** NextAuth.js handles Google OAuth and stores the access token in the JWT session. Server-side API routes in `src/app/api/calendar/` call the Google Calendar API using that token. The UI is a set of client components under `src/components/Calendar/` wired together in `src/app/calendar/page.js`.

**Tech Stack:** next-auth v4, googleapis, Framer Motion (already installed), Next.js 14 App Router

---

## Pre-requisite: Manual Google Cloud Setup

Before running any code, do this once in the browser:

1. Go to https://console.cloud.google.com → create or select a project
2. APIs & Services → Enable APIs → enable **Google Calendar API**
3. APIs & Services → Credentials → Create credentials → **OAuth 2.0 Client ID**
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:3000/api/auth/callback/google`
4. Copy the **Client ID** and **Client Secret**
5. In Google Calendar → Settings → add a new calendar named **"RDG.dev"** → copy its **Calendar ID** (looks like `abc123@group.calendar.google.com`)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/lib/authOptions.js` | Create | NextAuth config with Google provider + token callbacks |
| `src/app/api/auth/[...nextauth]/route.js` | Create | NextAuth route handler |
| `src/components/AuthProvider.jsx` | Create | Client-side SessionProvider wrapper |
| `src/app/layout.js` | Modify | Add AuthProvider |
| `src/app/api/calendar/events/route.js` | Create | GET (list) + POST (create) events |
| `src/app/api/calendar/events/[id]/route.js` | Create | PATCH (update) + DELETE events |
| `src/components/Calendar/CalendarHeader.jsx` | Create | Navigation, period label, view toggle, + Event button |
| `src/components/Calendar/EventBlock.jsx` | Create | Compact gold event block |
| `src/components/Calendar/CalendarGrid.jsx` | Create | Month view 7-column grid |
| `src/components/Calendar/WeekView.jsx` | Create | Week view with time slots |
| `src/components/Calendar/EventDetailPanel.jsx` | Create | Slide-in detail panel |
| `src/components/Calendar/EventForm.jsx` | Create | Create/edit modal form |
| `src/app/calendar/page.js` | Create | Main calendar page (protected) |
| `src/components/Navbar.jsx` | Modify | Add CALENDAR nav link |
| `.env.local.example` | Create | Environment variable template |

---

## Task 1: Install packages & create environment template

**Files:**
- Run: `npm install next-auth googleapis`
- Create: `.env.local.example`

- [ ] **Step 1: Install dependencies**

```bash
cd "C:/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
npm install next-auth googleapis
```

Expected output: `added N packages` with no errors.

- [ ] **Step 2: Create `.env.local.example`**

Create the file `.env.local.example` at the project root:

```
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
NEXTAUTH_SECRET=generate_with_openssl_rand_base64_32
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CALENDAR_ID=your_rdg_calendar_id@group.calendar.google.com
```

- [ ] **Step 3: Create `.env.local` with real values**

Copy `.env.local.example` to `.env.local` and fill in the real values from Google Cloud Console and Google Calendar settings. This file is already gitignored via `.env.*`.

- [ ] **Step 4: Verify build**

```bash
npm run build
```

Expected: build succeeds (no new errors — only the existing pages).

- [ ] **Step 5: Commit**

```bash
git add .env.local.example package.json package-lock.json
git commit -m "feat: install next-auth and googleapis dependencies"
```

---

## Task 2: Create authOptions + NextAuth route

**Files:**
- Create: `src/lib/authOptions.js`
- Create: `src/app/api/auth/[...nextauth]/route.js`

- [ ] **Step 1: Create `src/lib/authOptions.js`**

```js
import GoogleProvider from 'next-auth/providers/google';

export const authOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      authorization: {
        params: {
          scope: 'openid email profile https://www.googleapis.com/auth/calendar',
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.accessToken = account.access_token;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};
```

- [ ] **Step 2: Create `src/app/api/auth/[...nextauth]/route.js`**

```js
import NextAuth from 'next-auth';
import { authOptions } from '../../../../lib/authOptions';

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
```

- [ ] **Step 3: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add src/lib/authOptions.js src/app/api/auth/
git commit -m "feat: add NextAuth Google OAuth configuration"
```

---

## Task 3: Add AuthProvider to layout

**Files:**
- Create: `src/components/AuthProvider.jsx`
- Modify: `src/app/layout.js`

- [ ] **Step 1: Create `src/components/AuthProvider.jsx`**

```jsx
'use client';

import { SessionProvider } from 'next-auth/react';

export default function AuthProvider({ children }) {
  return <SessionProvider>{children}</SessionProvider>;
}
```

- [ ] **Step 2: Update `src/app/layout.js`**

Add the import and wrap the existing ThemeProvider tree with AuthProvider:

```js
import '../styles/globals.css';
import { ThemeProvider } from '../components/ThemeProvider';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import PageTransition from '../components/PageTransition';
import NetworkBackground from '../components/NetworkBackground';
import DataGrid from '../components/DataGrid';
import AuthProvider from '../components/AuthProvider';

export const metadata = {
  title: 'RDG. — Real Estate AI Automation',
  description: 'Randy de Groot — I build AI tools that automate real estate workflows.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="dark">
      <body style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <AuthProvider>
          <ThemeProvider>
            <DataGrid />
            <NetworkBackground
              nodeColor="#E8B931"
              pulseColor="#C49A1A"
              bgColor="transparent"
            />
            <div
              aria-hidden="true"
              style={{
                position: 'fixed',
                inset: 0,
                zIndex: 5,
                pointerEvents: 'none',
                background: 'linear-gradient(to bottom, var(--bg-primary) 0%, transparent 12%, transparent 88%, var(--bg-primary) 100%)',
              }}
            />
            <Navbar />
            <main style={{ flex: 1, overflowX: 'hidden', position: 'relative', zIndex: 6 }}>
              <PageTransition>{children}</PageTransition>
            </main>
            <Footer />
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add src/components/AuthProvider.jsx src/app/layout.js
git commit -m "feat: add AuthProvider wrapper to root layout"
```

---

## Task 4: GET/POST events API route

**Files:**
- Create: `src/app/api/calendar/events/route.js`

- [ ] **Step 1: Create `src/app/api/calendar/events/route.js`**

```js
import { getServerSession } from 'next-auth/next';
import { google } from 'googleapis';
import { authOptions } from '../../../../lib/authOptions';

function getCalendarClient(accessToken) {
  const auth = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
  );
  auth.setCredentials({ access_token: accessToken });
  return google.calendar({ version: 'v3', auth });
}

export async function GET(request) {
  const session = await getServerSession(authOptions);
  if (!session?.accessToken) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const start = searchParams.get('start');
  const end = searchParams.get('end');

  if (!start || !end) {
    return Response.json({ error: 'Missing start or end parameter' }, { status: 400 });
  }

  try {
    const calendar = getCalendarClient(session.accessToken);
    const response = await calendar.events.list({
      calendarId: process.env.GOOGLE_CALENDAR_ID,
      timeMin: start,
      timeMax: end,
      singleEvents: true,
      orderBy: 'startTime',
    });
    return Response.json(response.data.items ?? []);
  } catch (err) {
    console.error('Calendar GET error:', err.message);
    return Response.json({ error: 'Failed to fetch events' }, { status: 500 });
  }
}

export async function POST(request) {
  const session = await getServerSession(authOptions);
  if (!session?.accessToken) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const body = await request.json();
  const { title, startDateTime, endDateTime, description, location } = body;

  if (!title || !startDateTime || !endDateTime) {
    return Response.json({ error: 'title, startDateTime and endDateTime are required' }, { status: 400 });
  }

  try {
    const calendar = getCalendarClient(session.accessToken);
    const response = await calendar.events.insert({
      calendarId: process.env.GOOGLE_CALENDAR_ID,
      requestBody: {
        summary: title,
        description: description ?? '',
        location: location ?? '',
        start: { dateTime: startDateTime, timeZone: 'Europe/Amsterdam' },
        end: { dateTime: endDateTime, timeZone: 'Europe/Amsterdam' },
      },
    });
    return Response.json(response.data, { status: 201 });
  } catch (err) {
    console.error('Calendar POST error:', err.message);
    return Response.json({ error: 'Failed to create event' }, { status: 500 });
  }
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/app/api/calendar/
git commit -m "feat: add GET/POST calendar events API route"
```

---

## Task 5: PATCH/DELETE events API route

**Files:**
- Create: `src/app/api/calendar/events/[id]/route.js`

- [ ] **Step 1: Create `src/app/api/calendar/events/[id]/route.js`**

```js
import { getServerSession } from 'next-auth/next';
import { google } from 'googleapis';
import { authOptions } from '../../../../../lib/authOptions';

function getCalendarClient(accessToken) {
  const auth = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
  );
  auth.setCredentials({ access_token: accessToken });
  return google.calendar({ version: 'v3', auth });
}

export async function PATCH(request, { params }) {
  const session = await getServerSession(authOptions);
  if (!session?.accessToken) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { id } = params;
  const body = await request.json();
  const { title, startDateTime, endDateTime, description, location } = body;

  if (!title || !startDateTime || !endDateTime) {
    return Response.json({ error: 'title, startDateTime and endDateTime are required' }, { status: 400 });
  }

  try {
    const calendar = getCalendarClient(session.accessToken);
    const response = await calendar.events.patch({
      calendarId: process.env.GOOGLE_CALENDAR_ID,
      eventId: id,
      requestBody: {
        summary: title,
        description: description ?? '',
        location: location ?? '',
        start: { dateTime: startDateTime, timeZone: 'Europe/Amsterdam' },
        end: { dateTime: endDateTime, timeZone: 'Europe/Amsterdam' },
      },
    });
    return Response.json(response.data);
  } catch (err) {
    console.error('Calendar PATCH error:', err.message);
    return Response.json({ error: 'Failed to update event' }, { status: 500 });
  }
}

export async function DELETE(request, { params }) {
  const session = await getServerSession(authOptions);
  if (!session?.accessToken) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { id } = params;

  try {
    const calendar = getCalendarClient(session.accessToken);
    await calendar.events.delete({
      calendarId: process.env.GOOGLE_CALENDAR_ID,
      eventId: id,
    });
    return new Response(null, { status: 204 });
  } catch (err) {
    console.error('Calendar DELETE error:', err.message);
    return Response.json({ error: 'Failed to delete event' }, { status: 500 });
  }
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/app/api/calendar/events/[id]/
git commit -m "feat: add PATCH/DELETE calendar events API route"
```

---

## Task 6: CalendarHeader component

**Files:**
- Create: `src/components/Calendar/CalendarHeader.jsx`

- [ ] **Step 1: Create `src/components/Calendar/CalendarHeader.jsx`**

```jsx
'use client';

import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';

function getWeekStart(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = (day + 6) % 7;
  d.setDate(d.getDate() - diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getPeriodLabel(view, currentDate) {
  if (view === 'month') {
    return currentDate.toLocaleString('nl-NL', { month: 'long', year: 'numeric' });
  }
  const monday = getWeekStart(currentDate);
  const sunday = new Date(monday);
  sunday.setDate(sunday.getDate() + 6);
  const startLabel = monday.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' });
  const endLabel = sunday.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short', year: 'numeric' });
  return `${startLabel} — ${endLabel}`;
}

export default function CalendarHeader({ view, onViewChange, currentDate, onPrev, onNext, onNewEvent }) {
  const [hoveredView, setHoveredView] = React.useState(null);
  const label = getPeriodLabel(view, currentDate);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: 'var(--space-6)',
      flexWrap: 'wrap',
      gap: 'var(--space-4)',
    }}>

      {/* Left: prev / next */}
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        {[{ label: '←', action: onPrev }, { label: '→', action: onNext }].map(({ label: btn, action }) => (
          <button
            key={btn}
            onClick={action}
            style={{
              width: '2rem', height: '2rem',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              backgroundColor: 'transparent',
              border: '1px solid rgba(232,185,49,0.2)',
              color: 'var(--accent-secondary)',
              fontFamily: 'var(--font-heading)',
              fontSize: 'var(--text-base)',
              cursor: 'pointer',
              transition: 'border-color var(--transition-fast), color var(--transition-fast)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'var(--accent-primary)';
              e.currentTarget.style.color = 'var(--accent-primary)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'rgba(232,185,49,0.2)';
              e.currentTarget.style.color = 'var(--accent-secondary)';
            }}
          >
            {btn}
          </button>
        ))}
      </div>

      {/* Center: period label */}
      <h2 style={{
        fontFamily: 'var(--font-heading)',
        fontSize: 'var(--text-xl)',
        fontWeight: 700,
        color: 'var(--text-primary)',
        letterSpacing: '-0.02em',
        margin: 0,
        textTransform: 'capitalize',
      }}>
        {label}
      </h2>

      {/* Right: view toggle + new event button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-6)' }}>
        <LayoutGroup id="cal-view-toggle">
          <div style={{ display: 'flex', gap: 'var(--space-5)' }}>
            {[{ id: 'month', label: 'MAAND' }, { id: 'week', label: 'WEEK' }].map(v => (
              <div
                key={v.id}
                style={{ position: 'relative', cursor: 'pointer', paddingBottom: 'var(--space-1)' }}
                onClick={() => onViewChange(v.id)}
                onMouseEnter={() => setHoveredView(v.id)}
                onMouseLeave={() => setHoveredView(null)}
              >
                <span style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  letterSpacing: '0.12em',
                  color: view === v.id || hoveredView === v.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  transition: 'color var(--transition-fast)',
                }}>
                  {v.label}
                </span>

                <AnimatePresence>
                  {hoveredView === v.id && view !== v.id && (
                    <motion.span
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      exit={{ scaleX: 0 }}
                      transition={{ duration: 0.2, ease: 'easeOut' }}
                      style={{
                        position: 'absolute', bottom: 0, left: 0, right: 0,
                        height: '1px', backgroundColor: 'var(--accent-primary)',
                        transformOrigin: 'left',
                      }}
                    />
                  )}
                </AnimatePresence>

                {view === v.id && (
                  <motion.span
                    layoutId="cal-underline"
                    style={{
                      position: 'absolute', bottom: 0, left: 0, right: 0,
                      height: '1px', backgroundColor: 'var(--accent-primary)',
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </LayoutGroup>

        <button
          onClick={onNewEvent}
          style={{
            fontFamily: 'var(--font-heading)',
            fontSize: 'var(--text-xs)',
            fontWeight: 700,
            letterSpacing: '0.1em',
            color: '#1A1714',
            backgroundColor: 'var(--accent-primary)',
            border: 'none',
            padding: 'var(--space-2) var(--space-4)',
            cursor: 'pointer',
            transition: 'background-color var(--transition-fast)',
          }}
          onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
        >
          + EVENT
        </button>
      </div>
    </div>
  );
}
```

Note: add `import React, { useState } from 'react';` at the top of the file (needed for `React.useState`). Actually replace `React.useState` with `useState` and add the import:

```jsx
'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/components/Calendar/
git commit -m "feat: add CalendarHeader component"
```

---

## Task 7: EventBlock component

**Files:**
- Create: `src/components/Calendar/EventBlock.jsx`

- [ ] **Step 1: Create `src/components/Calendar/EventBlock.jsx`**

```jsx
'use client';

export default function EventBlock({ event, onClick, compact = true }) {
  const title = event.summary || '(Geen titel)';
  const isAllDay = !event.start?.dateTime;
  const time = isAllDay
    ? 'Hele dag'
    : new Date(event.start.dateTime).toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });

  return (
    <div
      onClick={() => onClick(event)}
      title={`${time} — ${title}`}
      style={{
        backgroundColor: 'var(--accent-primary)',
        color: '#1A1714',
        padding: compact ? '2px var(--space-2)' : 'var(--space-2) var(--space-3)',
        borderRadius: 'var(--radius-sm)',
        fontSize: 'var(--text-xs)',
        fontFamily: 'var(--font-heading)',
        fontWeight: 600,
        cursor: 'pointer',
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
        userSelect: 'none',
        transition: 'background-color var(--transition-fast)',
        marginBottom: compact ? '2px' : 0,
      }}
      onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
      onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
    >
      {compact ? `${time} ${title}` : title}
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/components/Calendar/EventBlock.jsx
git commit -m "feat: add EventBlock component"
```

---

## Task 8: CalendarGrid component (month view)

**Files:**
- Create: `src/components/Calendar/CalendarGrid.jsx`

- [ ] **Step 1: Create `src/components/Calendar/CalendarGrid.jsx`**

```jsx
'use client';

import EventBlock from './EventBlock';

const DAY_LABELS = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo'];

function getMonthCells(year, month) {
  const firstWeekday = new Date(year, month, 1).getDay(); // 0 = Sun
  const paddingStart = (firstWeekday + 6) % 7; // Convert to Mon = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < paddingStart; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

function getEventsForDay(events, year, month, day) {
  return events.filter(event => {
    const d = new Date(event.start?.dateTime || event.start?.date);
    return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
  });
}

export default function CalendarGrid({ currentDate, events, onEventClick, onDayClick }) {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const today = new Date();
  const isToday = (day) =>
    day === today.getDate() && month === today.getMonth() && year === today.getFullYear();

  const cells = getMonthCells(year, month);

  return (
    <div>
      {/* Day headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        marginBottom: 'var(--space-2)',
      }}>
        {DAY_LABELS.map(d => (
          <div key={d} style={{
            fontFamily: 'monospace',
            fontSize: '10px',
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            textAlign: 'center',
            padding: 'var(--space-2) 0',
          }}>
            {d}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        border: '1px solid var(--border-subtle)',
      }}>
        {cells.map((day, i) => {
          const dayEvents = day ? getEventsForDay(events, year, month, day) : [];
          const visibleEvents = dayEvents.slice(0, 3);
          const overflow = dayEvents.length - 3;

          return (
            <div
              key={i}
              onClick={() => day && onDayClick && onDayClick(new Date(year, month, day))}
              style={{
                minHeight: '100px',
                padding: 'var(--space-2)',
                borderRight: (i + 1) % 7 !== 0 ? '1px solid var(--border-subtle)' : 'none',
                borderBottom: i < cells.length - 7 ? '1px solid var(--border-subtle)' : 'none',
                backgroundColor: day ? 'transparent' : 'rgba(0,0,0,0.02)',
                outline: isToday(day) ? '1px solid var(--accent-primary)' : 'none',
                outlineOffset: '-1px',
                cursor: day ? 'default' : 'default',
                position: 'relative',
              }}
            >
              {day && (
                <>
                  <span style={{
                    display: 'block',
                    fontFamily: 'var(--font-heading)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: isToday(day) ? 700 : 400,
                    color: isToday(day) ? 'var(--accent-primary)' : 'var(--text-muted)',
                    marginBottom: 'var(--space-1)',
                    lineHeight: 1,
                  }}>
                    {day}
                  </span>
                  {visibleEvents.map(event => (
                    <EventBlock
                      key={event.id}
                      event={event}
                      onClick={onEventClick}
                      compact
                    />
                  ))}
                  {overflow > 0 && (
                    <span style={{
                      fontFamily: 'monospace',
                      fontSize: '10px',
                      color: 'var(--accent-secondary)',
                      letterSpacing: '0.04em',
                    }}>
                      +{overflow} meer
                    </span>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/components/Calendar/CalendarGrid.jsx
git commit -m "feat: add CalendarGrid month view component"
```

---

## Task 9: WeekView component

**Files:**
- Create: `src/components/Calendar/WeekView.jsx`

- [ ] **Step 1: Create `src/components/Calendar/WeekView.jsx`**

```jsx
'use client';

import EventBlock from './EventBlock';

const HOUR_HEIGHT = 56; // px per hour
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const DAY_LABELS = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo'];

function getWeekStart(date) {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - (day + 6) % 7);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getWeekDays(date) {
  const monday = getWeekStart(date);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function getEventsForDay(events, dayDate) {
  return events.filter(event => {
    if (!event.start?.dateTime) return false;
    const eventDate = new Date(event.start.dateTime);
    return eventDate.toDateString() === dayDate.toDateString();
  });
}

function getEventStyle(event) {
  const start = new Date(event.start.dateTime);
  const end = new Date(event.end.dateTime);
  const startMinutes = start.getHours() * 60 + start.getMinutes();
  const durationMinutes = Math.max((end - start) / 60000, 30);
  return {
    position: 'absolute',
    top: (startMinutes / 60) * HOUR_HEIGHT + 'px',
    height: (durationMinutes / 60) * HOUR_HEIGHT + 'px',
    left: '2px',
    right: '2px',
    zIndex: 1,
  };
}

function getCurrentTimeTop() {
  const now = new Date();
  return ((now.getHours() * 60 + now.getMinutes()) / 60) * HOUR_HEIGHT;
}

export default function WeekView({ currentDate, events, onEventClick }) {
  const weekDays = getWeekDays(currentDate);
  const today = new Date();
  const isToday = (d) => d.toDateString() === today.toDateString();
  const timeTop = getCurrentTimeTop();

  return (
    <div style={{ display: 'flex', overflowX: 'auto' }}>
      {/* Time labels column */}
      <div style={{ width: '48px', flexShrink: 0 }}>
        {/* Header spacer */}
        <div style={{ height: '48px' }} />
        {HOURS.map(h => (
          <div
            key={h}
            style={{
              height: HOUR_HEIGHT + 'px',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'flex-end',
              paddingRight: 'var(--space-2)',
              paddingTop: '2px',
            }}
          >
            <span style={{
              fontFamily: 'monospace',
              fontSize: '10px',
              color: 'var(--text-muted)',
              letterSpacing: '0.04em',
            }}>
              {h.toString().padStart(2, '0')}:00
            </span>
          </div>
        ))}
      </div>

      {/* Day columns */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', minWidth: 0 }}>
        {weekDays.map((day, i) => {
          const dayEvents = getEventsForDay(events, day);
          const isCurrentDay = isToday(day);

          return (
            <div key={i} style={{ borderLeft: '1px solid var(--border-subtle)' }}>
              {/* Day header */}
              <div style={{
                height: '48px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                borderBottom: '1px solid var(--border-subtle)',
                backgroundColor: isCurrentDay ? 'rgba(232,185,49,0.05)' : 'transparent',
              }}>
                <span style={{
                  fontFamily: 'monospace',
                  fontSize: '10px',
                  fontWeight: 600,
                  letterSpacing: '0.1em',
                  color: isCurrentDay ? 'var(--accent-primary)' : 'var(--text-muted)',
                  textTransform: 'uppercase',
                }}>
                  {DAY_LABELS[i]}
                </span>
                <span style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: isCurrentDay ? 700 : 400,
                  color: isCurrentDay ? 'var(--accent-primary)' : 'var(--text-secondary)',
                }}>
                  {day.getDate()}
                </span>
              </div>

              {/* Time grid */}
              <div style={{ position: 'relative', height: HOUR_HEIGHT * 24 + 'px' }}>
                {/* Hour lines */}
                {HOURS.map(h => (
                  <div key={h} style={{
                    position: 'absolute',
                    top: h * HOUR_HEIGHT + 'px',
                    left: 0, right: 0,
                    height: '1px',
                    backgroundColor: 'var(--border-subtle)',
                  }} />
                ))}

                {/* Current time indicator */}
                {isCurrentDay && (
                  <div style={{
                    position: 'absolute',
                    top: timeTop + 'px',
                    left: 0, right: 0,
                    height: '2px',
                    backgroundColor: 'var(--accent-primary)',
                    zIndex: 2,
                    boxShadow: '0 0 6px rgba(232,185,49,0.5)',
                  }} />
                )}

                {/* Events */}
                {dayEvents.map(event => (
                  <div key={event.id} style={getEventStyle(event)}>
                    <EventBlock event={event} onClick={onEventClick} compact={false} />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/components/Calendar/WeekView.jsx
git commit -m "feat: add WeekView component"
```

---

## Task 10: EventDetailPanel component

**Files:**
- Create: `src/components/Calendar/EventDetailPanel.jsx`

- [ ] **Step 1: Create `src/components/Calendar/EventDetailPanel.jsx`**

```jsx
'use client';

import { motion, AnimatePresence } from 'framer-motion';

function formatDateTime(event) {
  if (event.start?.dateTime) {
    const start = new Date(event.start.dateTime);
    const end = new Date(event.end.dateTime);
    const dateStr = start.toLocaleDateString('nl-NL', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    const startTime = start.toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });
    const endTime = end.toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });
    return { date: dateStr, time: `${startTime} – ${endTime}` };
  }
  if (event.start?.date) {
    const d = new Date(event.start.date);
    return {
      date: d.toLocaleDateString('nl-NL', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
      time: 'Hele dag',
    };
  }
  return { date: '—', time: '—' };
}

export default function EventDetailPanel({ event, onClose, onEdit, onDelete }) {
  if (!event) return null;

  const { date, time } = formatDateTime(event);

  return (
    <AnimatePresence>
      {event && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, zIndex: 50,
              backgroundColor: 'rgba(0,0,0,0.3)',
            }}
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            style={{
              position: 'fixed',
              top: '50%', right: 'var(--space-6)',
              transform: 'translateY(-50%)',
              zIndex: 51,
              width: '320px',
              maxWidth: 'calc(100vw - var(--space-12))',
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderLeft: '3px solid var(--accent-primary)',
              backdropFilter: 'blur(40px)',
              WebkitBackdropFilter: 'blur(40px)',
              padding: 'var(--space-8)',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            {/* Close button */}
            <button
              onClick={onClose}
              style={{
                position: 'absolute', top: 'var(--space-4)', right: 'var(--space-4)',
                background: 'none', border: 'none',
                color: 'var(--text-muted)', cursor: 'pointer',
                fontFamily: 'var(--font-heading)', fontSize: 'var(--text-lg)',
                lineHeight: 1, padding: 'var(--space-1)',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; }}
            >
              ×
            </button>

            {/* Tag */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-4)' }}>
              <span style={{
                display: 'inline-block', width: 6, height: 6,
                borderRadius: '50%', background: 'var(--accent-primary)',
                boxShadow: '0 0 6px rgba(232,185,49,0.6)',
              }} />
              <span style={{
                fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
                letterSpacing: '0.15em', textTransform: 'uppercase',
                color: 'var(--accent-secondary)',
              }}>
                RDG.DEV EVENT
              </span>
            </div>

            {/* Title */}
            <h3 style={{
              fontFamily: 'var(--font-heading)', fontSize: 'var(--text-lg)',
              fontWeight: 700, color: 'var(--text-primary)',
              letterSpacing: '-0.01em', marginBottom: 'var(--space-5)',
              paddingRight: 'var(--space-8)',
            }}>
              {event.summary || '(Geen titel)'}
            </h3>

            {/* Date & time */}
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <p style={{
                fontFamily: 'monospace', fontSize: 'var(--text-xs)',
                color: 'var(--text-muted)', marginBottom: 'var(--space-1)',
                letterSpacing: '0.06em', textTransform: 'capitalize',
              }}>
                {date}
              </p>
              <p style={{
                fontFamily: 'var(--font-heading)', fontSize: 'var(--text-base)',
                color: 'var(--accent-secondary)', fontWeight: 600,
              }}>
                {time}
              </p>
            </div>

            {/* Location */}
            {event.location && (
              <div style={{ marginBottom: 'var(--space-4)' }}>
                <p style={{
                  fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  color: 'var(--text-muted)', marginBottom: 'var(--space-1)',
                }}>
                  LOCATIE
                </p>
                <p style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                  {event.location}
                </p>
              </div>
            )}

            {/* Description */}
            {event.description && (
              <div style={{ marginBottom: 'var(--space-6)' }}>
                <p style={{
                  fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  color: 'var(--text-muted)', marginBottom: 'var(--space-1)',
                }}>
                  OMSCHRIJVING
                </p>
                <p style={{
                  fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)',
                  color: 'var(--text-secondary)', lineHeight: 1.6,
                }}>
                  {event.description}
                </p>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-6)' }}>
              <button
                onClick={() => onEdit(event)}
                style={{
                  flex: 1,
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 700, letterSpacing: '0.1em',
                  color: '#1A1714', backgroundColor: 'var(--accent-primary)',
                  border: 'none', padding: 'var(--space-2) var(--space-4)',
                  cursor: 'pointer', transition: 'background-color var(--transition-fast)',
                }}
                onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
              >
                BEWERKEN
              </button>
              <button
                onClick={() => {
                  if (window.confirm(`"${event.summary}" verwijderen?`)) onDelete(event.id);
                }}
                style={{
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 700, letterSpacing: '0.1em',
                  color: 'rgba(239,68,68,0.8)', backgroundColor: 'transparent',
                  border: '1px solid rgba(239,68,68,0.3)',
                  padding: 'var(--space-2) var(--space-4)',
                  cursor: 'pointer', transition: 'border-color var(--transition-fast), color var(--transition-fast)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'rgba(239,68,68,0.7)';
                  e.currentTarget.style.color = 'rgba(239,68,68,1)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'rgba(239,68,68,0.3)';
                  e.currentTarget.style.color = 'rgba(239,68,68,0.8)';
                }}
              >
                VERWIJDEREN
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/components/Calendar/EventDetailPanel.jsx
git commit -m "feat: add EventDetailPanel slide-in component"
```

---

## Task 11: EventForm component (modal)

**Files:**
- Create: `src/components/Calendar/EventForm.jsx`

- [ ] **Step 1: Create `src/components/Calendar/EventForm.jsx`**

```jsx
'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function toLocalDateTimeInputValue(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  const pad = n => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISOWithTimezone(localDateTimeValue) {
  if (!localDateTimeValue) return '';
  return new Date(localDateTimeValue).toISOString();
}

const inputStyle = {
  width: '100%',
  backgroundColor: 'var(--bg-secondary)',
  border: '1px solid var(--border-default)',
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-heading)',
  fontSize: 'var(--text-sm)',
  padding: 'var(--space-3) var(--space-4)',
  outline: 'none',
  boxSizing: 'border-box',
  transition: 'border-color var(--transition-fast)',
};

const labelStyle = {
  display: 'block',
  fontFamily: 'monospace',
  fontSize: '10px',
  fontWeight: 600,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: 'var(--space-2)',
};

export default function EventForm({ event, onSave, onClose, loading }) {
  const isEditing = !!event?.id;

  const defaultStart = () => {
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(d.getHours() + 1);
    return d.toISOString();
  };
  const defaultEnd = () => {
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(d.getHours() + 2);
    return d.toISOString();
  };

  const [title, setTitle] = useState(event?.summary ?? '');
  const [startDateTime, setStartDateTime] = useState(
    toLocalDateTimeInputValue(event?.start?.dateTime ?? defaultStart())
  );
  const [endDateTime, setEndDateTime] = useState(
    toLocalDateTimeInputValue(event?.end?.dateTime ?? defaultEnd())
  );
  const [description, setDescription] = useState(event?.description ?? '');
  const [location, setLocation] = useState(event?.location ?? '');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (!title.trim()) { setError('Titel is verplicht.'); return; }
    if (!startDateTime || !endDateTime) { setError('Begin- en eindtijd zijn verplicht.'); return; }
    if (new Date(endDateTime) <= new Date(startDateTime)) {
      setError('Eindtijd moet na begintijd liggen.'); return;
    }
    onSave({
      id: event?.id,
      title: title.trim(),
      startDateTime: toISOWithTimezone(startDateTime),
      endDateTime: toISOWithTimezone(endDateTime),
      description: description.trim(),
      location: location.trim(),
    });
  };

  return (
    <AnimatePresence>
      <motion.div
        key="form-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 60,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 'var(--space-6)',
        }}
      >
        <motion.div
          key="form-modal"
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.98 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          onClick={e => e.stopPropagation()}
          style={{
            width: '100%',
            maxWidth: '480px',
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderLeft: '3px solid var(--accent-primary)',
            backdropFilter: 'blur(40px)',
            WebkitBackdropFilter: 'blur(40px)',
            padding: 'var(--space-8)',
            boxShadow: 'var(--shadow-lg)',
            position: 'relative',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-6)' }}>
            <span style={{
              display: 'inline-block', width: 6, height: 6,
              borderRadius: '50%', background: 'var(--accent-primary)',
              boxShadow: '0 0 6px rgba(232,185,49,0.6)',
            }} />
            <span style={{
              fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
              letterSpacing: '0.15em', textTransform: 'uppercase',
              color: 'var(--accent-secondary)',
            }}>
              {isEditing ? 'EVENT BEWERKEN' : 'NIEUW EVENT'}
            </span>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            {/* Title */}
            <div>
              <label style={labelStyle}>Titel *</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Event naam"
                style={inputStyle}
                onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
              />
            </div>

            {/* Start / End */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
              <div>
                <label style={labelStyle}>Begintijd *</label>
                <input
                  type="datetime-local"
                  value={startDateTime}
                  onChange={e => setStartDateTime(e.target.value)}
                  style={inputStyle}
                  onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                  onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
                />
              </div>
              <div>
                <label style={labelStyle}>Eindtijd *</label>
                <input
                  type="datetime-local"
                  value={endDateTime}
                  onChange={e => setEndDateTime(e.target.value)}
                  style={inputStyle}
                  onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                  onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
                />
              </div>
            </div>

            {/* Location */}
            <div>
              <label style={labelStyle}>Locatie</label>
              <input
                type="text"
                value={location}
                onChange={e => setLocation(e.target.value)}
                placeholder="Optionele locatie"
                style={inputStyle}
                onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
              />
            </div>

            {/* Description */}
            <div>
              <label style={labelStyle}>Omschrijving</label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Optionele omschrijving"
                rows={3}
                style={{
                  ...inputStyle,
                  resize: 'vertical',
                  fontFamily: 'var(--font-body)',
                  lineHeight: 1.6,
                }}
                onFocus={e => { e.target.style.borderColor = 'var(--accent-primary)'; }}
                onBlur={e => { e.target.style.borderColor = 'var(--border-default)'; }}
              />
            </div>

            {/* Error */}
            {error && (
              <p style={{
                fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                color: 'rgba(239,68,68,0.9)', margin: 0,
              }}>
                {error}
              </p>
            )}

            {/* Buttons */}
            <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
              <button
                type="submit"
                disabled={loading}
                style={{
                  flex: 1,
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 700, letterSpacing: '0.1em',
                  color: loading ? 'rgba(26,23,20,0.5)' : '#1A1714',
                  backgroundColor: loading ? 'rgba(232,185,49,0.4)' : 'var(--accent-primary)',
                  border: 'none', padding: 'var(--space-3) var(--space-4)',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'background-color var(--transition-fast)',
                }}
                onMouseEnter={e => { if (!loading) e.currentTarget.style.backgroundColor = 'var(--accent-primary-hover)'; }}
                onMouseLeave={e => { if (!loading) e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
              >
                {loading ? 'OPSLAAN...' : 'OPSLAAN'}
              </button>
              <button
                type="button"
                onClick={onClose}
                style={{
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)',
                  fontWeight: 600, letterSpacing: '0.1em',
                  color: 'var(--text-secondary)', backgroundColor: 'transparent',
                  border: '1px solid var(--border-default)',
                  padding: 'var(--space-3) var(--space-4)',
                  cursor: 'pointer', transition: 'border-color var(--transition-fast), color var(--transition-fast)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--border-default)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }}
              >
                ANNULEREN
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/components/Calendar/EventForm.jsx
git commit -m "feat: add EventForm modal component"
```

---

## Task 12: Calendar page

**Files:**
- Create: `src/app/calendar/page.js`

- [ ] **Step 1: Create `src/app/calendar/page.js`**

```jsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession, signIn } from 'next-auth/react';
import AnimateIn from '../../components/AnimateIn';
import CalendarHeader from '../../components/Calendar/CalendarHeader';
import CalendarGrid from '../../components/Calendar/CalendarGrid';
import WeekView from '../../components/Calendar/WeekView';
import EventDetailPanel from '../../components/Calendar/EventDetailPanel';
import EventForm from '../../components/Calendar/EventForm';

function getWeekStart(date) {
  const d = new Date(date);
  d.setDate(d.getDate() - (d.getDay() + 6) % 7);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getMonthRange(date) {
  const start = new Date(date.getFullYear(), date.getMonth(), 1);
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 1);
  return { start, end };
}

function getWeekRange(date) {
  const start = getWeekStart(date);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  return { start, end };
}

export default function CalendarPage() {
  const { data: session, status } = useSession();

  const [view, setView] = useState('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [formEvent, setFormEvent] = useState(null);  // null = closed, {} = create, event = edit
  const [formOpen, setFormOpen] = useState(false);
  const [formLoading, setFormLoading] = useState(false);

  // Redirect to Google login if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      signIn('google');
    }
  }, [status]);

  const fetchEvents = useCallback(async () => {
    if (!session) return;
    setLoadingEvents(true);
    setFetchError(null);
    try {
      const { start, end } = view === 'month'
        ? getMonthRange(currentDate)
        : getWeekRange(currentDate);
      const res = await fetch(
        `/api/calendar/events?start=${start.toISOString()}&end=${end.toISOString()}`
      );
      if (!res.ok) throw new Error('Ophalen mislukt');
      const data = await res.json();
      setEvents(Array.isArray(data) ? data : []);
    } catch (err) {
      setFetchError(err.message);
    } finally {
      setLoadingEvents(false);
    }
  }, [session, view, currentDate]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handlePrev = () => {
    const d = new Date(currentDate);
    if (view === 'month') d.setMonth(d.getMonth() - 1);
    else d.setDate(d.getDate() - 7);
    setCurrentDate(d);
  };

  const handleNext = () => {
    const d = new Date(currentDate);
    if (view === 'month') d.setMonth(d.getMonth() + 1);
    else d.setDate(d.getDate() + 7);
    setCurrentDate(d);
  };

  const handleSave = async ({ id, title, startDateTime, endDateTime, description, location }) => {
    setFormLoading(true);
    try {
      const body = { title, startDateTime, endDateTime, description, location };
      const res = id
        ? await fetch(`/api/calendar/events/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          })
        : await fetch('/api/calendar/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
      if (!res.ok) throw new Error('Opslaan mislukt');
      setFormOpen(false);
      setFormEvent(null);
      setSelectedEvent(null);
      await fetchEvents();
    } catch (err) {
      alert(err.message);
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`/api/calendar/events/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Verwijderen mislukt');
      setSelectedEvent(null);
      await fetchEvents();
    } catch (err) {
      alert(err.message);
    }
  };

  const openCreateForm = () => {
    setFormEvent({});
    setFormOpen(true);
    setSelectedEvent(null);
  };

  const openEditForm = (event) => {
    setFormEvent(event);
    setFormOpen(true);
    setSelectedEvent(null);
  };

  // Loading / auth states
  if (status === 'loading') {
    return (
      <section style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'monospace', fontSize: 'var(--text-sm)', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
          LADEN...
        </span>
      </section>
    );
  }

  if (!session) return null;

  return (
    <section style={{ minHeight: '100vh', padding: 'var(--space-20) var(--space-6)' }}>
      <div style={{ width: '100%', maxWidth: '1100px', margin: '0 auto' }}>

        <AnimateIn delay={0.05}>
          {/* Page header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-6)' }}>
            <span style={{
              display: 'inline-block', width: 6, height: 6,
              borderRadius: '50%', background: 'var(--accent-primary)',
              boxShadow: '0 0 8px rgba(232,185,49,0.7)',
            }} />
            <span style={{
              fontFamily: 'monospace', fontSize: '10px', fontWeight: 600,
              letterSpacing: '0.18em', textTransform: 'uppercase',
              color: 'var(--accent-secondary)',
            }}>
              RDG.DEV // KALENDER
            </span>
          </div>

          <div style={{ marginBottom: 'var(--space-10)' }}>
            <div style={{
              fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)',
              fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em',
              color: 'var(--text-primary)',
            }}>
              AGENDA
            </div>
            <div style={{
              fontFamily: 'var(--font-heading)', fontSize: 'var(--text-3xl)',
              fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em',
              color: 'transparent', WebkitTextStroke: '1px rgba(232,185,49,0.5)',
            }}>
              DASHBOARD.
            </div>
          </div>
        </AnimateIn>

        <AnimateIn delay={0.1}>
          <CalendarHeader
            view={view}
            onViewChange={setView}
            currentDate={currentDate}
            onPrev={handlePrev}
            onNext={handleNext}
            onNewEvent={openCreateForm}
          />

          {/* Error state */}
          {fetchError && (
            <div style={{
              padding: 'var(--space-4)',
              border: '1px solid rgba(239,68,68,0.3)',
              backgroundColor: 'rgba(239,68,68,0.05)',
              marginBottom: 'var(--space-4)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--text-sm)', color: 'rgba(239,68,68,0.9)' }}>
                {fetchError}
              </span>
              <button
                onClick={fetchEvents}
                style={{
                  fontFamily: 'var(--font-heading)', fontSize: 'var(--text-xs)', fontWeight: 700,
                  letterSpacing: '0.1em', color: 'var(--accent-secondary)',
                  background: 'none', border: 'none', cursor: 'pointer',
                }}
              >
                OPNIEUW
              </button>
            </div>
          )}

          {/* Loading overlay */}
          {loadingEvents && (
            <div style={{
              textAlign: 'center', padding: 'var(--space-8)',
              fontFamily: 'monospace', fontSize: 'var(--text-xs)',
              color: 'var(--text-muted)', letterSpacing: '0.12em',
            }}>
              EVENTS LADEN...
            </div>
          )}

          {/* Calendar views */}
          {!loadingEvents && view === 'month' && (
            <CalendarGrid
              currentDate={currentDate}
              events={events}
              onEventClick={setSelectedEvent}
            />
          )}

          {!loadingEvents && view === 'week' && (
            <WeekView
              currentDate={currentDate}
              events={events}
              onEventClick={setSelectedEvent}
            />
          )}
        </AnimateIn>
      </div>

      {/* Detail panel */}
      {selectedEvent && (
        <EventDetailPanel
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onEdit={openEditForm}
          onDelete={handleDelete}
        />
      )}

      {/* Create / Edit form */}
      {formOpen && (
        <EventForm
          event={formEvent && formEvent.id ? formEvent : null}
          onSave={handleSave}
          onClose={() => { setFormOpen(false); setFormEvent(null); }}
          loading={formLoading}
        />
      )}
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 3: Manual browser verification**

```bash
npm run dev
```

1. Navigate to `http://localhost:3000/calendar`
2. You should be redirected to Google login
3. After login, the calendar page should appear with the month view
4. Navigate between months (← →)
5. Switch to week view
6. Click "+ EVENT" → form modal opens
7. Fill in title, start/end time → click OPSLAAN → event appears in calendar
8. Click on an event → detail panel slides in from the right
9. Click BEWERKEN → form opens pre-filled
10. Click VERWIJDEREN → confirm dialog → event removed

- [ ] **Step 4: Commit**

```bash
git add src/app/calendar/
git commit -m "feat: add protected calendar page with month/week views"
```

---

## Task 13: Add Calendar link to Navbar

**Files:**
- Modify: `src/components/Navbar.jsx`

- [ ] **Step 1: Update `NAV_LINKS` in `src/components/Navbar.jsx`**

Change the `NAV_LINKS` array from:

```js
const NAV_LINKS = [
  { label: 'WORK',  href: '/work' },
  { label: 'ABOUT', href: '/about' },
  { label: 'BLOG',  href: '/blog' },
];
```

To:

```js
const NAV_LINKS = [
  { label: 'WORK',     href: '/work' },
  { label: 'ABOUT',    href: '/about' },
  { label: 'BLOG',     href: '/blog' },
  { label: 'CALENDAR', href: '/calendar' },
];
```

- [ ] **Step 2: Verify build**

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Manual verification**

```bash
npm run dev
```

1. Check the navbar shows CALENDAR link
2. Active gold underline appears when on `/calendar`
3. Mobile menu shows CALENDAR link in the overlay

- [ ] **Step 4: Commit**

```bash
git add src/components/Navbar.jsx
git commit -m "feat: add Calendar link to Navbar"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Protected Google OAuth login — Task 2 + 3 + page `useSession`
- ✅ Dedicated "RDG.dev" calendar via `GOOGLE_CALENDAR_ID` env var — Tasks 4 + 5
- ✅ Month view — Task 8 + CalendarGrid
- ✅ Week view — Task 9 + WeekView
- ✅ View toggle — CalendarHeader
- ✅ Compact event blocks, click to open detail — EventBlock + EventDetailPanel
- ✅ Create event — EventForm (POST)
- ✅ Edit event — EventForm (PATCH)
- ✅ Delete event — EventDetailPanel (DELETE)
- ✅ Error handling: form validation, API errors, retry button — Tasks 4/5/12
- ✅ Session expired → redirect to login — `useEffect` in page
- ✅ Honey & smoke design system — all components use CSS vars + inline styles
- ✅ Navbar link — Task 13
