/* SPDX-License-Identifier: MIT -- original mock API surface; not production headers. */
#ifndef MOCK_GL_H
#define MOCK_GL_H
#include <stddef.h>
typedef unsigned GLenum;
typedef unsigned GLuint;
typedef int GLint;
typedef float GLfloat;
#define GL_FALSE 0
#define GL_NO_ERROR 0
#define GL_VENDOR 1
#define GL_RENDERER 2
#define GL_VERSION 3
#define GL_SHADING_LANGUAGE_VERSION 4
#define GL_VERTEX_SHADER 5
#define GL_FRAGMENT_SHADER 6
#define GL_COMPILE_STATUS 7
#define GL_LINK_STATUS 8
#define GL_ARRAY_BUFFER 9
#define GL_STATIC_DRAW 10
#define GL_FLOAT 11
#define GL_COLOR_BUFFER_BIT 12
#define GL_TRIANGLES 13
GLuint glCreateShader(GLenum);
void glShaderSource(GLuint,int,const char *const *,const int *);
void glCompileShader(GLuint);
void glGetShaderiv(GLuint,GLenum,GLint *);
void glDeleteShader(GLuint);
const unsigned char *glGetString(GLenum);
GLuint glCreateProgram(void);
void glAttachShader(GLuint,GLuint);
void glBindAttribLocation(GLuint,GLuint,const char *);
void glLinkProgram(GLuint);
void glGetProgramiv(GLuint,GLenum,GLint *);
GLint glGetUniformLocation(GLuint,const char *);
void glGenBuffers(int,GLuint *);
void glBindBuffer(GLenum,GLuint);
void glBufferData(GLenum,ptrdiff_t,const void *,GLenum);
void glUseProgram(GLuint);
void glVertexAttribPointer(GLuint,int,GLenum,unsigned char,int,const void *);
void glEnableVertexAttribArray(GLuint);
GLenum glGetError(void);
void glViewport(int,int,int,int);
void glUniform1f(GLint,GLfloat);
void glClearColor(GLfloat,GLfloat,GLfloat,GLfloat);
void glClear(GLenum);
void glDrawArrays(GLenum,int,int);
void glDeleteBuffers(int,const GLuint *);
void glDeleteProgram(GLuint);
#endif
