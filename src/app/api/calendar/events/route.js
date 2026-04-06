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
