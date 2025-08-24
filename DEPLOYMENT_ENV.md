# Deployment Environment Variables

## Required Environment Variables for Koyeb

Copy these EXACT values to your Koyeb deployment settings:

```
SUPABASE_URL=https://jqdqrirpndtzgbtkeigm.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpxZHFyaXJwbmR0emdidGtlaWdtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwMzQ0MTMsImV4cCI6MjA3MTYxMDQxM30.jo50MI15-q89nCDOqwz7cvYQ546T3UssOjgPuuZcXpU
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpxZHFyaXJwbmR0emdidGtlaWdtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjAzNDQxMywiZXhwIjoyMDcxNjEwNDEzfQ._pk0g-bwDHRTKJjN5TVsv_eOkjoY1WuUfTeHQgQLduM
SECRET_KEY=your-super-secret-flask-key-change-this-in-production
FLASK_ENV=production
```

## How to Update on Koyeb:

1. Go to your Koyeb dashboard
2. Click on your service: `deep-audy-wotbix`
3. Go to **Settings** → **Environment Variables**
4. Add/Update each variable above (WITHOUT quotes)
5. Click **Deploy** to apply changes

## Important Notes:

- Do NOT include quotes around the values in Koyeb
- Make sure there are no extra spaces
- The service will automatically restart after updating

## Verify Deployment:

After updating, check:
1. Service logs for any errors
2. Try signup at: https://deep-audy-wotbix-9060bbad.koyeb.app/auth/signup
3. Check Supabase dashboard for new users

## Database Setup:

Make sure you've run `supabase_setup.sql` in your Supabase project:
- Project: `jqdqrirpndtzgbtkeigm`
- Tables needed: users, ad_accounts, mcp_sessions