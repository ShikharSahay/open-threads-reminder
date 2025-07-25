package handlers

import (
    "encoding/json"
    "net/http"

    "github.com/labstack/echo/v4"
)

// GetSample - Sample GET API
func (c *Container) GetSample(ctx echo.Context) error {
    return ctx.String(http.StatusOK, "sample response")
}

// GetSample - Sample GET API
func (c *Container) PostSample(ctx echo.Context) error {
  bodyMap := make(map[string]interface{})
  err := json.NewDecoder(ctx.Request().Body).Decode(&bodyMap)
  if err != nil {
      return ctx.String(http.StatusBadRequest, err.Error())
  }

  sampleField, ok := bodyMap["sample_field"].(string)
  if !ok {
      return ctx.String(http.StatusBadRequest, "expected sample_field of type string")
  }

  _ = sampleField

  return ctx.JSON(http.StatusOK, bodyMap)
}
