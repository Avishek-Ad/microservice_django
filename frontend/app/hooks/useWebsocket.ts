"use client";

import { useEffect, useRef } from "react";

export default function useWebsocket(
  url: string,
  onMessage: (data: any) => void
) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!url) return;
    // console.log("URL", url)

    let ws: WebSocket | null = null;

    const setupWebsocket = async () => {

      // ws connection
      ws = new WebSocket(`${process.env.NEXT_PUBLIC_BACKEND_WEBSOCKET_URL}/${url}`);
      wsRef.current = ws;

      // on ws connects
      ws.onopen = () => {
        console.log("websocket connected");
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage(data);
      };

      // on ws disconnects
      ws.onclose = () => {
        console.log("Websocket disconnected");
      };

      // on ws errors
      ws.onerror = (error) => {
        console.log("Websocket error :", error);
      };
    };

    setupWebsocket();

    // closes the connection when the component unmounts
    return () => {
      if (ws) {
        console.log("Closing websocket.....");
        ws.close();
      }
    };
  }, [url]);

  // this function sends data to the server
  const sendEvent = (data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn("WebSocket is not open. Cannot send message");
    }
  };

  return { ws: wsRef, sendEvent };
}