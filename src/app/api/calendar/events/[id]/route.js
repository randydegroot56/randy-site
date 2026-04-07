import { getServerSession } from 'next-auth/next';
import { authOptions } from '../../../../../lib/authOptions';
import { getCalendarClient } from '../../../../../lib/calendarClient';

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
