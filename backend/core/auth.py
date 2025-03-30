import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from gotrue.errors import AuthApiError
# jwt import might not be needed if using supabase client's get_user
# from jwt import decode as jwt_decode, ExpiredSignatureError, InvalidTokenError

# Use absolute imports from 'backend' root
from core.config import settings

# Initialize Supabase client for backend operations (using Service Role Key)
# Note: Using Service Role Key bypasses RLS. Use with caution.
# For user-specific actions where RLS is desired, you might need a different client
# initialized with the user's JWT if Supabase-py supports that flow easily,
# or rely on frontend client for RLS-aware operations.
supabase_url: str = settings.SUPABASE_URL
supabase_key: str = settings.SUPABASE_SERVICE_ROLE_KEY # Use service role for verification
# Set schema to 'auth' when interacting with auth endpoints if needed,
# but for JWT verification, the key itself is often sufficient with pyjwt.
# options = ClientOptions(schema="auth") # Usually not needed for just get_user
supabase_admin_client: Client = create_client(supabase_url, supabase_key)

# OAuth2 scheme to extract token from Authorization header ("Bearer <token>")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # tokenUrl is dummy here, we verify Supabase token

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency to verify Supabase JWT and return user data.
    Raises HTTPException for invalid/expired tokens or auth errors.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Use Supabase client's built-in method to verify JWT and get user
        # This implicitly uses the SERVICE_ROLE_KEY provided during client init
        response = supabase_admin_client.auth.get_user(token)
        user = response.user
        if not user:
            # This case might occur if the token is valid but user doesn't exist? Unlikely with Supabase.
            raise credentials_exception
        # Return user data as a dictionary (or Pydantic model if preferred)
        # Ensure the returned object is serializable if needed directly in response models
        # Convert UserResponse object to dict
        user_dict = {
            "id": str(user.id), # Convert UUID to string
            "email": user.email,
            "aud": user.aud,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
            # Add other relevant fields as needed
        }
        return user_dict
    except AuthApiError as e:
        # Handle specific errors from Supabase GoTrue
        print(f"Supabase Auth API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {e.message}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Catch any other unexpected errors during verification
        print(f"Unexpected error during token verification: {e}")
        raise credentials_exception

# Example of how to use the dependency in an endpoint:
# from fastapi import APIRouter
# from core.auth import get_current_user # Note absolute import here too if used elsewhere
# router = APIRouter()
# @router.get("/users/me")
# async def read_users_me(current_user: dict = Depends(get_current_user)):
#     return current_user
