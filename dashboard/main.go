package main

import (
    "dashboard/apiserver"

    "os"
)

var (
    Addr string
    Port string
)

var help bool

func getEnv(key, fallback string) string {
    if value, ok := os.LookupEnv(key); ok {
        return value
    }
    return fallback
}

// TODO: change main function
func main() {
    Addr = getEnv("YB_OPEN_THREADS_REMINDER_ADDR", "127.0.0.1")
    Port = getEnv("YB_OPEN_THREADS_REMINDER_PORT", "18080")

    apiserver.Start(Addr, Port)
}