; extends

; it can be # %% [markdown] or # %% [md]
((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @injection.content)))
  (#lua-match? @_mdcomment "^# %%%% %[markdown%]")
  (#set! injection.language "markdown"))

((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @injection.content)))
  (#lua-match? @_mdcomment "^# %%%% %[markdown%]")
  (#set! injection.language "markdown_inline"))

((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @injection.content)))
  (#lua-match? @_mdcomment "^# %%%% %[md%]")
  (#set! injection.language "markdown"))

((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @injection.content)))
  (#lua-match? @_mdcomment "^# %%%% %[md%]")
  (#set! injection.language "markdown_inline"))
