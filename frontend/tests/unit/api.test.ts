import { describe, it, expect } from 'vitest';
import { ApiException, ApiError } from '../../src/lib/api';

describe('ApiException', () => {
  it('correctly maps error properties conforming to API specification (docs/04 section 1)', () => {
    const errorPayload: ApiError = {
      code: 'validation_error',
      message: 'Invalid password format',
      details: [{ field: 'password', issue: 'must be at least 10 characters' }],
      request_id: 'req-12345',
    };

    const ex = new ApiException(422, errorPayload);

    expect(ex.status).toBe(422);
    expect(ex.code).toBe('validation_error');
    expect(ex.message).toBe('Invalid password format');
    expect(ex.details).toHaveLength(1);
    expect(ex.details[0].field).toBe('password');
    expect(ex.requestId).toBe('req-12345');
  });

  it('provides default code when not supplied in payload', () => {
    const errorPayload: ApiError = {
      code: '',
      message: 'Server error',
    };

    const ex = new ApiException(500, errorPayload);
    expect(ex.code).toBe('unknown_error');
    expect(ex.message).toBe('Server error');
    expect(ex.details).toEqual([]);
  });
});
