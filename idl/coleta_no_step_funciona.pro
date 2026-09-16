; Aceita s/S/sim/Sim/SIM etc.: o resto do programa compara so com a primeira
; letra minuscula ('s','n','u','c','l'); sem isto 'sim' era lido como nao.
function resposta, texto
  return, strlowcase(strmid(strtrim(texto, 2), 0, 1))
end

pro coleta_no_step_funciona

;********************************variaveis

var = [[5]]
fita = intarr(30)
teste = intarr(30)
coluna= intarr(5)
linha= intarr(5)
energia = intarr(5)
posicao = intarr(2)
largura = 15
aux2=0
E_i = 0 
times = 0
g=0
i=0
h=0
z=0 
result=0
experiencia = ''
vrein=0
direc = ''
arq  = ''
arq2 = ''
arq3 = ''
arq4 = ""
desj = ''
desj1 = ''
desj2= ''
desj3= ''
desj4= ''
soma = 0
somatotal = 0.00

Device, pseudo_color=24
Device, Get_Visual_Depth=thisDepth
IF thisDepth GT 8 THEN Device, Decomposed=0

;*************************************************Informacoes iniciais

read, 'Entre com o nome do experimento: ', experiencia
read, 'Diretorio das figuras: ', direc
read, 'Energia inicial:', aux
read, 'Energia final:', E_f
read, 'passo (step para coleta da curva): ', passo
read, arq2, prompt = 'Entre com o nome do arquivo para salvar os dados: '

;*************************************************rotina que verifica se todos os arquivos existem!

var = long(aux)

;openw,1 , 'arquivos_problema.txt'
j=0
while (var le E_f) do begin
	arq=string(direc)+strcompress(string(var),/remove_all)+'.jpg'
	var = long(var) + 1
	result=file_test(arq)
	if (result eq 1) then begin
		j = j +1
	endif	 
endwhile
energias = intarr(j)

var = long(aux)
h=0
while (var le E_f) do begin
 arq=string(direc)+strcompress(string(var),/remove_all)+'.jpg'
 result=file_test(arq)
 if (result eq 1) then begin
 	energias(h) = var
	h = h + 1
 endif  
 var = long(var) + 1
endwhile

print, 'Energias Existentes',  energias
;**********************************************************fim da checagem dos arquivos - def. iniciais e def. vetores

reinicio: read, desj, prompt = 'Deseja manter o numero de pontos para interpolar energia vs posicao padrao(5) - (s/n): '
desj = resposta(desj)
if (desj eq 'n') then begin
	dnovo: read, times, prompt='Entre com a novo numero de pontos: '
	if (times eq 0) then begin
		goto, dnovo
	endif
endif else begin 
	times = 5
endelse
;************************************reinicio de uma nova coleta
outraves:

read, desj, prompt='Deseja manter a largura do spot padrao (15 x 15 pixel) - (s/n): '
desj = resposta(desj)
if (desj eq 'n') then begin
	read, largura, prompt='Entre com a nova largura: '
endif 

tamanho = j
;print, tamanho
Intensity_min = lon64arr(tamanho)
Intensity_max = lon64arr(tamanho)
Intensity = dblarr(tamanho); Vetor de dados intensidade e energia
Intensit = dblarr(tamanho)
Energy= lon64arr(tamanho)


E_i=long(aux)

;************************************reinicio de uma nova coleta
;outraves:
if (vrein = 1) then begin
	var = E_i
	aux2=0
	i=0
	g=0
	
endif

;****************************************************************************coleta de coordenadas para acompanhar os padroes

while (var le E_f) and (aux2 ne times) do begin
 
 arq=string(direc)+strcompress(string(var),/remove_all)+'.jpg'
 ;print, direc
 ;print, arq 
 read_jpeg, arq, image, Order=1
 window,1,TITLE = 'Energia= '+strcompress(string(var))+' eV', retain=2,xsize=640,ysize=480 
 tvscl, image
 print, 'Energia: ', var,'eV'
 read, desj2, PROMPT='grava estas coordenadas? (s/n) '
 desj2 = resposta(desj2)
 if (desj2 eq 's') and (aux2 ne 5) then begin
	print, 'Anote os valores de coluna e linha atraves do profile'
        energia(aux2)=var
        profiles_g, image, posicao
	coluna(aux2) = posicao[0]
        linha(aux2) = posicao[1]
	coluna_aux = posicao[0]
	linha_aux = posicao[1]
	print, coluna, linha
        aux2=aux2+1
	if ((coluna_aux-floor(largura/2)) lt 0) then col1=0 else col1 = (coluna_aux - floor(largura/2))
	if ((coluna_aux+floor(largura/2)) gt 639) then col2 = 639 else col2 = (coluna_aux + floor(largura/2))
	if ((linha_aux-floor(largura/2)) lt 0) then lin1=0 else lin1 = (linha_aux - floor(largura/2))
        if ((linha_aux+floor(largura/2)) gt 479) then lin2 = 479 else lin2 = (linha_aux + floor(largura/2))
	spot=image(col1:col2,lin1:lin2)
        img_size= size(spot, /Dimensions)
        window,2,title='spot', retain=2,xsize=200,ysize=200
        tv, spot
  	if (i eq 0) then begin
		read, desj4, prompt='Gostaria de arquivar esta imagem e tirar um profile da imagem? (s/n/u = nunca mais perguntar) '
		desj4 = resposta(desj4)
		if (desj4 eq 's') or (desj4 eq 'S') then begin
			arq3='figuras_'+strcompress(string(z),/remove_all)+strcompress(string(var),/remove_all)+'.dat'
			openw,2, arq3
			printf,2, '*****************************surface****************************************'
			printf,2, spot
			printf,2, '*****************************profile****************************************'
			wdelete
			tv, image
			r = profile(image)
			printf,2, r
			close,2
		endif else begin
			if (desj4 eq 'u') or (desj4 eq 'U') then i=i+1
		endelse
	endif
		
	read, desj3, prompt='resultado final da janela foi satisfatorio? (s = continuar / n = voltar) '
	desj3 = resposta(desj3)
	if (desj3 eq 'n') then begin 
		aux2 = aux2 - 1
		goto, denovo 
	endif
	denovo: read, 'Entre com nova energia: ', var2
 	if (var2 ge E_i) and (var2 le E_f) then begin
		var2 = uint(var2)
         	var=uint(var2)
		arq=string(direc)+strcompress(string(var),/remove_all)+'.jpg'
		result=file_test(arq)
		if (result ne 1) then begin 
			print, energias
			goto, denovo
		endif
 	endif else begin
		print, 'Energia inexistente= ', var2
        	goto, denovo
 	endelse
 endif else begin
	goto, denovo
 endelse
endwhile 

wdelete

result = poly_fit(energia,coluna,3)
result2 = poly_fit(energia,linha,3)

;******************************************************************inicio da coleta da curva

var2 = energias(0)
window,1, TITLE = 'gráficos', retain=2,xsize=640,ysize=480
z=0
repeat begin
	read, desj, prompt='Subtrai Bachground pela aproximacao de (c)oluna ou (l)inha: '
	desj = resposta(desj)
endrep until (desj eq 'c') or (desj eq 'l')

while (var2 le E_f+1) do begin

 arq=string(direc)+strcompress(string(var2),/remove_all)+'.jpg'
 read_jpeg, arq, image, Order=1
 c_poly = result(0)+(result(1)*var2)+(result(2)*var2*var2)+(result(3)*var2*var2*var2)
 l_poly = result2(0)+(result2(1)*var2)+(result2(2)*var2*var2)+(result2(3)*var2*var2*var2)
 if ((round(c_poly)-floor(largura/2)) lt 0) then col1=0 else col1 = (round(c_poly) - floor(largura/2))
 if ((round(c_poly)+floor(largura/2)) gt 639) then col2 = 639 else col2 = (round(c_poly) + floor(largura/2))
 if ((round(l_poly)-floor(largura/2)) lt 0) then lin1=0 else lin1 = (round(l_poly)- floor(largura/2))
 if ((round(l_poly)+floor(largura/2)) gt 479) then lin2 = 479 else lin2 = (round(l_poly) + floor(largura/2))
 spot=image(col1:col2,lin1:lin2)
 ;tv, spot
 maximo = max(spot)
 for x=col1, col2, 1 do begin
 	for y=lin1, lin2, 1 do begin
		spt = image(x,y)
		if spt ge maximo then begin
			if (x ge c_poly-3) and (x le c_poly+3) then c_poly = x
			if (y ge l_poly-3) and (y le l_poly+3) then l_poly = y
		endif
	endfor
 endfor
 if ((round(c_poly)-floor(largura/2)) lt 0) then col1=0 else col1 = (round(c_poly) - floor(largura/2))
 if ((round(c_poly)+floor(largura/2)) gt 639) then col2 = 639 else col2 = (round(c_poly) + floor(largura/2))
 if ((round(l_poly)-floor(largura/2)) lt 0) then lin1=0 else lin1 = (round(l_poly)- floor(largura/2))
 if ((round(l_poly)+floor(largura/2)) gt 479) then lin2 = 479 else lin2 = (round(l_poly) + floor(largura/2))
 spot=image(col1:col2,lin1:lin2)
 ;tv, spot, 320,220
 if ((round(c_poly)-30) lt 0) then col1a=0 else col1a = (round(c_poly)-30)
 if ((round(c_poly)+30) gt 639) then col2a = 639 else col2a = (round(c_poly)+30)
 if ((round(l_poly)-30) lt 0) then lin1a= 0 else lin1a = (round(l_poly)-30)
 if ((round(l_poly)+30) gt 479) then lin2a = 479 else lin2a = (round(l_poly)+30)
 spot2=image(col1a:col2a,lin1a:lin2a)
 tv, spot2, 300,220

 wait, 1
 img_size= size(spot, /Dimensions)
 somatotal = 0
 maximo = max(spot)
 minimo = min(spot)
 soma = 0
 i=0
 
 ; extrair background - modelo descrito no artigo da Vacuum, 65 (2002) 121-1256; "Spot intensity processing in LEED images"
 ; Aproximacao de colunas e linhas

 if (desj eq 'C') or (desj eq 'c') then begin
       	y=0
	for x=0, img_size(0)-1,1 do begin
	    teste = rheed_profile (spot, [x,y], [x,img_size(1)-1], xx, yy)
	    y_final = img_size(1)-1
	    y_inicial = 0
	    for yy=0, img_size(1)-1, 1 do begin
	    	if (spot[x,yy] lt spot[x,y_inicial]) and (yy le (img_size(1)-1)/4) then y_inicial = yy
		if (spot[x,yy] lt spot[x,y_final]) and (yy gt (img_size(1)-1)*3/4) then y_final = yy
	    endfor
	    for yy=0, img_size(1)-1, 1 do begin
	        fita[yy] = (long(spot[x,y_final])-long(spot[x,y_inicial]))*yy/long(img_size(1)-1) + long(spot[x,y_inicial])
	    endfor
	    soma = long(soma) + long(teste - fita)
	    plot, teste, linestyle = 0
	    oplot, fita, linestyle = 1
	    oplot, teste - fita, linestyle = 2
	    oplot, soma, linestyle = 1
	   if (g eq 1) then begin
            read, desj1, prompt='Deseja salvar graficos em arquivo(s/n): '
            desj1 = resposta(desj1)
	    if (desj1 eq 'S') or (desj1 eq 's') then begin
                openw,3, strcompress('graficos_'+string(var2)+'_'+string(i)+'_linha.dat')
                for yy=0, img_size(1)-1, 1 do begin
			printf,3, yy, '   ', teste[yy],'	',fita[yy]
		endfor
                close,3
		i=i+1
            endif else g = g +1
	   endif 
	endfor
 endif 
 if (desj eq 'l') or (desj eq 'L') then begin 
	x=0
        for y=0, img_size(1)-1,1 do begin
            teste = rheed_profile (spot, [x,y], [img_size(0)-1,y], xx, yy)
            x_final = img_size(0)-1
	    x_inicial = 0
	    for xx=0, img_size(0)-1, 1 do begin
	    	if (spot[xx,y] lt spot[x_inicial,y]) and (xx le (img_size(0)-1)/4) then x_inicial = xx
            	if (spot[xx,y] lt spot[x_final,y]) and (xx gt (img_size(0)-1)*3/4) then x_final = xx
            endfor
            for xx=0, img_size(0)-1, 1 do begin
            	fita[xx] = (long(spot[x_final,y])-long(spot[x_inicial,y]))*xx/long(img_size(0)-1) + long(spot[x_inicial,y])
            endfor
            soma = long(soma) + long(teste - fita)
            plot, teste, linestyle = 0
            oplot, fita, linestyle = 1
            oplot, teste - fita, linestyle = 2
            oplot, soma, linestyle = 1
	   if (g eq 0) then begin 
            read, desj1, prompt='Deseja salvar graficos em arquivo(s/n): '
            desj1 = resposta(desj1)
	    if (desj1 eq 'S') or (desj1 eq 's') then begin
		openw,3, strcompress('graficos_'+string(var2)+'_'+string(i)+'_coluna.dat')
	     	for yy=0, img_size(1)-1, 1 do begin
                        printf,3, yy, '    ', teste[yy],'   ',fita[yy]
                endfor
		close,3
	        i=i+1
	    endif else g=g+1
	   endif
	endfor
 endif
 
 ;fim da subtracao do Background e inicio da transferencia dos valores para os vetores e plot na tela
 
 plot, soma, TITLE = 'Energia= '+strcompress(string(var2))+' eV'
 for f=0 , img_size(0)-1, 1 do somatotal = ulong(somatotal + soma[f])
 Intensity(z) = somatotal
 Energy(z) = var2
 i=i+1
 print, var2
 if (var2 ne E_f) then begin
	z=z+1
 	var2 = energias(z)
 endif else begin
 	var2 = E_f+2
 endelse

endwhile
plot, Energy, Intensity, linestyle = 1,  XTITLE= 'Energy (eV)',YTITLE= 'Intensity (u.a.)'

wait, 5

maximo=Max(Intensity)
;print, maximo, 'z= ', z
for n=0, z-1, 1 do Intensit(n)=double(Intensity(n)/maximo)
;print, 'normalização= ', Intensit
PLOT, Energy, Intensit, TITLE='Intensidade normalizada e Smoothing FFT (3th degree)'

wait, 5

smoothing = smooth(Intensit, 3, /EDGE_TRUNCATE)
smoothing2 = smooth(Intensity, 3,/EDGE_TRUNCATE)

wait,3

oplot, Energy, smoothing,linestyle=2, thick=5
;oplot, Energy, smoothing2, linestyle=1, thick=3

wait, 20

;**************************************grava dados normalizados e smooth **************

openw,1,arq2
printf,1,experiencia
printf,1,'Valor de normalização=', maximo
printf,1,"energia ", " intensidade ", "intensidade - smoothing" 

for n=0, z-1, 1 do printf, 1,  Energy(n), Intensity(n), smoothing2(n) 

close,1

;**************************************************************************************

wdelete

repeat begin
        read,desj, prompt='Deseja coletar outras curvas de direcoes diferentes? (s/n) '
        desj = resposta(desj)
	if (desj eq 's') or (desj eq 'S') then begin 
		read, arq2, prompt = 'Entre com o nome do arquivo para salvar os dados: '
		vrein = 1
		goto, outraves
	endif
endrep until (desj eq 'n')

fim:
exit
end
