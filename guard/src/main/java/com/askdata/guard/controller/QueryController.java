package com.askdata.guard.controller;

import com.askdata.guard.model.QueryRequest;
import com.askdata.guard.model.QueryResponse;
import com.askdata.guard.service.QueryExecutionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping
public class QueryController {

    private final QueryExecutionService executionService;

    @Autowired
    public QueryController(QueryExecutionService executionService) {
        this.executionService = executionService;
    }

    @PostMapping("/query")
    public ResponseEntity<QueryResponse> handleQuery(@RequestBody QueryRequest request) {
        QueryResponse response = executionService.execute(request);
        if (response.isSuccess()) {
            return ResponseEntity.ok(response);
        } else {
            return ResponseEntity.badRequest().body(response);
        }
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("AskData Query Guard is healthy and enforcing AST security policies.");
    }
}
