export type paths = {
  '/api/v1/auth/login': {
    post: {
      requestBody: {
        content: {
          'application/json': components['schemas']['LoginRequest'];
        };
      };
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['TokenResponse'];
          };
        };
      };
    };
  };
  '/api/v1/auth/register': {
    post: {
      requestBody: {
        content: {
          'application/json': components['schemas']['RegisterRequest'];
        };
      };
      responses: {
        201: {
          content: {
            'application/json': components['schemas']['TokenResponse'];
          };
        };
      };
    };
  };
  '/api/v1/profile': {
    get: {
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['ProfileResponse'];
          };
        };
      };
    };
    patch: {
      requestBody: {
        content: {
          'application/json': components['schemas']['ProfileUpdate'];
        };
      };
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['ProfileResponse'];
          };
        };
      };
    };
  };
  '/api/v1/wardrobe': {
    get: {
      responses: {
        200: {
          content: {
            'application/json': components['schemas']['WardrobeItem'][];
          };
        };
      };
    };
  };
};

export type components = {
  schemas: {
    LoginRequest: {
      email: string;
      password: string;
    };
    RegisterRequest: {
      email: string;
      password: string;
      name?: string | null;
    };
    TokenResponse: {
      access_token: string;
      token_type: string;
    };
    ProfileResponse: {
      user_id: string;
      name?: string | null;
      styles?: string[] | null;
      fav_colors?: string[] | null;
    };
    ProfileUpdate: {
      name?: string | null;
      styles?: string[] | null;
      fav_colors?: string[] | null;
    };
    WardrobeItem: {
      id: string;
      name: string;
      category: string;
      color: string;
      image_url?: string | null;
    };
  };
};
