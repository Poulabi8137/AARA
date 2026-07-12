import io, { Socket } from 'socket.io-client';

let socket: Socket | null = null;

export const initWebSocket = (token?: string): Socket => {
  if (socket) return socket;

  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

  socket = io(wsUrl, {
    auth: token
      ? {
          token,
        }
      : undefined,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5,
  });

  socket.on('connect', () => {
  });

  socket.on('disconnect', () => {
  });

  socket.on('error', () => {
  });

  return socket;
};

export const getWebSocket = (): Socket | null => {
  return socket;
};

export const disconnectWebSocket = (): void => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};

export const subscribeToAgentUpdates = (
  callback: (data: unknown) => void
): (() => void) => {
  const ws = getWebSocket();
  if (!ws) {
    return () => {};
  }

  ws.on('agent:update', callback);

  return () => {
    ws.off('agent:update', callback);
  };
};

export const subscribeToMonitoringDashboard = (
  researchId: string,
  callback: (data: unknown) => void
): (() => void) => {
  const ws = getWebSocket();
  if (!ws) return () => {};

  ws.emit('subscribe:monitoring', { researchId });
  ws.on(`monitoring:${researchId}`, callback);

  return () => {
    ws.emit('unsubscribe:monitoring', { researchId });
    ws.off(`monitoring:${researchId}`, callback);
  };
};

export const sendAgentCommand = (command: string, payload: unknown): void => {
  const ws = getWebSocket();
  if (!ws) {
    return;
  }

  ws.emit('agent:command', { command, payload });
};
