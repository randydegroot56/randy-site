import { google } from 'googleapis';

export function getCalendarClient(accessToken) {
  const auth = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
  );
  auth.setCredentials({ access_token: accessToken });
  return google.calendar({ version: 'v3', auth });
}
