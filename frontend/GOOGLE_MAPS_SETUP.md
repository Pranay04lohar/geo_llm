# Google Maps Integration Setup

## Step 1: Get Google Maps API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Maps JavaScript API**
   - **Static Maps API**
4. Go to "Credentials" and create an API Key
5. **Important**: Restrict the API key to your domain for security

## Step 2: Add API Key to Environment

Create a `.env.local` file in the `frontend` directory with:

```env
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

Replace `your_actual_api_key_here` with your real Google Maps API key.

## Step 3: Restart Development Server

After adding the API key, restart your development server:

```bash
npm run dev
```

## Step 4: Verify Integration

- The map should now use Google Maps tiles
- You should see high-quality Google Maps imagery
- Both satellite and street view modes should work
- No console warnings about missing API key

## Troubleshooting

If you see console warnings about missing API key:
1. Check that `.env.local` file exists in the frontend directory
2. Verify the API key is correct
3. Restart the development server
4. Check browser console for any errors

## API Key Security

- Never commit your API key to version control
- Use domain restrictions in Google Cloud Console
- Monitor API usage to avoid unexpected charges
- Consider using environment-specific keys for development/production

