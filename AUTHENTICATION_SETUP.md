# Authentication Setup - Fixed

## Summary of Issues Fixed

1. **Database Connection**: Fixed Railway PostgreSQL connection issues with fallback to SQLite for local development
2. **Admin Page**: Fixed hardcoded API URL to use dynamic origin
3. **User Authentication**: Ensured proper user creation and password reset functionality
4. **Railway Deployment**: Updated configuration to use the new startup script

## Current Setup

### User Credentials
- **Email**: `jkuhns13@gmail.com`
- **Password**: `481816Test!`
- **Role**: Admin user with full access

### Database Configuration
- **Local Development**: SQLite (`app.db`)
- **Railway Production**: PostgreSQL (automatically detected)
- **Fallback**: If Railway database is unreachable locally, falls back to SQLite

## How to Use

### Local Development

1. **Start the application**:
   ```bash
   python start_app.py
   ```

2. **Access the admin console**:
   - URL: `http://127.0.0.1:5000/admin`
   - Login with: `jkuhns13@gmail.com` / `481816Test!`

3. **Test authentication**:
   ```bash
   python test_auth_fix.py
   ```

### Railway Production

1. **Deploy**: Push to Railway (uses `railway.toml` configuration)
2. **Access**: `https://your-app.railway.app/admin`
3. **Login**: Same credentials work in production

## Available Scripts

### Setup & Management
- `setup_auth.py` - Complete authentication setup
- `init_database.py` - Initialize database with default admin user
- `reset_user_password.py` - Reset any user's password
- `start_app.py` - Start application with proper setup

### Testing
- `test_auth_fix.py` - Test authentication endpoints
- `debug_auth.py` - Debug authentication issues

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password with token

### Admin (requires `Authorization: Bearer admin-access`)
- `GET /api/admin/users` - List all users
- `POST /api/admin/users` - Create new user
- `POST /api/admin/users/{id}/reset-password` - Reset user password
- `DELETE /api/admin/users/{id}` - Delete user
- `GET /api/admin/stats` - Get user statistics

### Debug
- `GET /debug/users` - List users (no auth required)
- `GET /debug/reset-password/{user_id}/{new_password}` - Emergency password reset

## Admin Console Features

1. **User Management**
   - View all users with details
   - Create new users
   - Reset passwords
   - Delete users

2. **Statistics Dashboard**
   - Total users count
   - Active users count
   - Recent logins

3. **Quick Actions**
   - Refresh user list
   - Export users to CSV

## Troubleshooting

### Cannot Login
```bash
python reset_user_password.py
```

### Database Issues
```bash
python init_database.py
```

### Test Endpoints
```bash
python test_auth_fix.py
```

### Check User List
Visit: `http://127.0.0.1:5000/debug/users`

## Security Notes

- Admin access uses simple bearer token authentication
- Passwords are hashed using Werkzeug's security functions
- JWT tokens expire after 30 days
- CORS is configured for frontend integration

## Next Steps

1. **Start the app**: `python start_app.py`
2. **Login to admin**: `http://127.0.0.1:5000/admin`
3. **Create additional users** as needed
4. **Deploy to Railway** for production use

The authentication system is now fully functional for both local development and Railway deployment!