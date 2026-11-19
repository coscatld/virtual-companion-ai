package com.example.vr_gfriend.common.config;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class ApiErrors {
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Result<Void>> invalidFields(MethodArgumentNotValidException error) {
        var fieldError = error.getBindingResult().getFieldError();
        String message = fieldError == null ? "请求内容有误" : fieldError.getDefaultMessage();
        return ResponseEntity.badRequest().body(Result.error(HttpStatus.BAD_REQUEST.value(), message));
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Result<Void>> statusError(ResponseStatusException error) {
        return ResponseEntity.status(error.getStatusCode())
                .headers(error.getHeaders())
                .contentType(MediaType.APPLICATION_JSON)
                .body(Result.error(error.getStatusCode().value(), error.getReason()));
    }
}
