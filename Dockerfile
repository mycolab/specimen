FROM ubuntu:latest
ENV DEBIAN_FRONTEND="noninteractive"

RUN apt clean
RUN apt-get update \
 && apt-get install -y build-essential git libtool-bin autopoint autotools-dev autoconf pkg-config \
    libncurses5-dev libncursesw5-dev gettext software-properties-common curl cpio python3 python3-pip vim

# add files
ADD /blast /blast

# compile and install blast
WORKDIR /blast
RUN ./configure
RUN make
RUN make install

# install edirect tools
RUN perl -MNet::FTP -e '$ftp = new Net::FTP("ftp.ncbi.nlm.nih.gov", Passive => 1); $ftp->login; $ftp->binary; $ftp->get("/entrez/entrezdirect/edirect.tar.gz");'
RUN gunzip -c edirect.tar.gz | tar xf - && rm edirect.tar.gz && cp -r edirect/* /usr/local/bin

# add transmute for XML transform
RUN  nquire -dwn ftp.ncbi.nlm.nih.gov entrez/entrezdirect transmute.Linux.gz
RUN  gunzip -f transmute.Linux.gz
RUN  chmod +x transmute.Linux
RUN  mv transmute.Linux /usr/local/bin

# import sequences and create a BLAST database
RUN mkdir mycolabdb blastdb queries fasta results
COPY update-data.sh /usr/local/bin
COPY start-blast.sh /usr/local/bin

# start container
ENTRYPOINT ["/usr/local/bin/start-blast.sh"]
CMD ["--api"]

# # optionally: install and update nucleotide database
# CMD ["--update", "--api"]
