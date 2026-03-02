import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    // Should redirect to login since not authenticated
    expect(document.body).toBeTruthy();
  });

  it('shows login page for unauthenticated users', () => {
    render(<App />);
    expect(screen.getByText(/Sign In/i)).toBeTruthy();
  });
});
