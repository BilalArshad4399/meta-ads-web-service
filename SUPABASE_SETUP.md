# Supabase Setup Guide

This application uses Supabase as its primary database. Follow these steps to set it up.

## Step 1: Create a Supabase Project

1. Go to [Supabase](https://supabase.com) and sign up/login
2. Click "New Project" and fill in:
   - Project name: `meta-ads-service` (or your preferred name)
   - Database Password: Choose a strong password
   - Region: Choose the closest to your users
3. Wait for the project to be created (takes about 2 minutes)

## Step 2: Get Your Project Credentials

Once your project is ready:

1. Go to Settings → API
2. Copy these values:
   - **Project URL**: `https://[YOUR-PROJECT-REF].supabase.co`
   - **Anon/Public Key**: Your public API key

## Step 3: Set Up Database Tables

1. Go to SQL Editor in your Supabase dashboard
2. Copy and paste the contents of `supabase_setup.sql` file
3. Click "Run" to create the tables

## Step 4: Configure Your Application

1. Create a `.env` file in your project root:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Supabase credentials:
   ```env
   # Supabase Configuration (REQUIRED)
   SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   
   # Flask Configuration
   SECRET_KEY=your-secret-key-here
   ```

## Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 6: Run the Application

```bash
python wsgi.py
```

## How It Works

The application now uses Supabase as its only database:

- **User Registration**: Creates users directly in Supabase
- **Authentication**: Validates credentials against Supabase data
- **Ad Accounts**: Stores Meta ad account information in Supabase
- **Sessions**: Manages MCP sessions in Supabase

## Benefits

- ✅ No local database needed
- ✅ Data persists across deployments
- ✅ Works seamlessly across multiple instances
- ✅ Built-in backup and recovery
- ✅ Real-time capabilities (if needed)

## Deployment

For production deployments, set these environment variables:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SECRET_KEY=your-secret-key
```

## Testing

Run the test script to verify your Supabase connection:

```bash
python test_supabase.py
```

## Troubleshooting

### Connection errors?
- Verify `SUPABASE_URL` is correct
- Check `SUPABASE_ANON_KEY` is valid
- Ensure tables are created (run `supabase_setup.sql`)

### Authentication issues?
- Check that the users table exists
- Verify password hashing is working
- Check logs for specific error messages

## Security Notes

- Never commit `.env` file to git
- Use environment variables in production
- Consider enabling Row Level Security (RLS) in Supabase for production
- Rotate your API keys regularly