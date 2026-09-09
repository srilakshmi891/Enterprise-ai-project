export const getApiErrorMessage = (err: any, fallbackMessage: string): string => {
  if (!err) return fallbackMessage;

  // Network error or server unreachable
  if (!err.response) {
    if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
      return 'Unable to connect to the server. Please check your backend connection.';
    }
    return err.message || fallbackMessage;
  }

  const status = err.response.status;
  const detail = err.response.data?.detail;

  // 400 Bad Request or 409 Conflict (e.g. Username/email already exists)
  if (status === 400 || status === 409) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: any) => d.msg || d).join(', ');
    }
    return 'Username or email already exists.';
  }

  // 401 Unauthorized
  if (status === 401) {
    if (typeof detail === 'string') return detail;
    return 'Invalid credentials. Please try again.';
  }

  // 422 Unprocessable Entity (Validation Error)
  if (status === 422) {
    if (Array.isArray(detail)) {
      return detail
        .map((d: any) => {
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : '';
          const msg = d.msg || 'Invalid value';
          return field && field !== 'body' ? `${field}: ${msg}` : msg;
        })
        .join('. ');
    }
    if (typeof detail === 'string') return detail;
    return 'Please check the registration details.';
  }

  // 500 Internal Server Error
  if (status === 500) {
    return 'Server error. Please try again.';
  }

  if (typeof detail === 'string') return detail;

  return fallbackMessage;
};
