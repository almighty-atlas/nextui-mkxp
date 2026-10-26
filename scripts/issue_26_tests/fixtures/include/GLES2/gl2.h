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
typedef GLuint (*PFNGLCREATESHADERPROC)(GLenum);
typedef void (*PFNGLSHADERSOURCEPROC)(GLuint,int,const char *const *,const int *);
typedef void (*PFNGLCOMPILESHADERPROC)(GLuint);
typedef void (*PFNGLGETSHADERIVPROC)(GLuint,GLenum,GLint *);
typedef void (*PFNGLDELETESHADERPROC)(GLuint);
typedef const unsigned char * (*PFNGLGETSTRINGPROC)(GLenum);
typedef GLuint (*PFNGLCREATEPROGRAMPROC)(void);
typedef void (*PFNGLATTACHSHADERPROC)(GLuint,GLuint);
typedef void (*PFNGLBINDATTRIBLOCATIONPROC)(GLuint,GLuint,const char *);
typedef void (*PFNGLLINKPROGRAMPROC)(GLuint);
typedef void (*PFNGLGETPROGRAMIVPROC)(GLuint,GLenum,GLint *);
typedef GLint (*PFNGLGETUNIFORMLOCATIONPROC)(GLuint,const char *);
typedef void (*PFNGLGENBUFFERSPROC)(int,GLuint *);
typedef void (*PFNGLBINDBUFFERPROC)(GLenum,GLuint);
typedef void (*PFNGLBUFFERDATAPROC)(GLenum,ptrdiff_t,const void *,GLenum);
typedef void (*PFNGLUSEPROGRAMPROC)(GLuint);
typedef void (*PFNGLVERTEXATTRIBPOINTERPROC)(GLuint,int,GLenum,unsigned char,int,const void *);
typedef void (*PFNGLENABLEVERTEXATTRIBARRAYPROC)(GLuint);
typedef GLenum (*PFNGLGETERRORPROC)(void);
typedef void (*PFNGLVIEWPORTPROC)(int,int,int,int);
typedef void (*PFNGLUNIFORM1FPROC)(GLint,GLfloat);
typedef void (*PFNGLCLEARCOLORPROC)(GLfloat,GLfloat,GLfloat,GLfloat);
typedef void (*PFNGLCLEARPROC)(GLenum);
typedef void (*PFNGLDRAWARRAYSPROC)(GLenum,int,int);
typedef void (*PFNGLDELETEBUFFERSPROC)(int,const GLuint *);
typedef void (*PFNGLDELETEPROGRAMPROC)(GLuint);
#endif
