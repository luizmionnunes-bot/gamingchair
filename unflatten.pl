#!/usr/bin/perl
use strict; use warnings;
my $in = shift or die "usage\n";
open my $fh,'<',$in or die $!; my @lines=<$fh>; close $fh;

my %arrays; my @gens;
for (my $i=0;$i<@lines;$i++){
  my $l=$lines[$i];
  if ($l =~ /local (\w+) = \{\s*$/){
    my $name=$1; my @vals; my $j=$i+1;
    while ($j<@lines && $lines[$j] !~ /^\s*\}/){ while($lines[$j]=~/(-?\d+)/g){push @vals,$1;} $j++; }
    $arrays{$name}=[@vals];
  } elsif ($l =~ /local (\w+) = \{(.+)\}/){
    my ($name,$body)=($1,$2); my @vals=($body=~/(-?\d+)/g); $arrays{$name}=[@vals] if @vals;
  }
  if ($l =~ /local function (\w+)\(([^)]*)\)/){
    my ($name,$plist)=($1,$2);
    my @params=map{(my $x=$_)=~s/\s//g;$x} split/,/,$plist;
    for (my $k=$i+1;$k<=$i+5 && $k<@lines;$k++){
      my $ex;
      if ($lines[$k] =~ /local \w+ = (.+?)\s*$/){ $ex=$1; }
      elsif ($lines[$k] =~ /\w+\[\w+\] = (.+?)\s*$/){ $ex=$1; }
      if (defined $ex){
        $ex=~s/;.*//;
        next if $ex=~/^\s*\w+\[\w+\]\s*$/;   # bare memo read (e.g. return t2[p1])
        push @gens, {name=>$name, line=>$i, params=>\@params, expr=>$ex, arrays=>{%arrays}};
        last;
      }
    }
  }
}
my %by_name; push @{$by_name{$_->{name}}}, $_ for @gens;

sub pick_gen {
  my ($name,$arity,$L)=@_; my $best;
  for my $g (@{$by_name{$name}||[]}){
    next unless scalar(@{$g->{params}})==$arity;
    next if $g->{line} > $L;
    $best=$g if !$best || $g->{line} > $best->{line};
  }
  return $best;
}
sub evalexpr {
  my ($expr,$map,$arr)=@_; my $e=$expr; my $guard=0;
  while ($e =~ /(\w+)\[(\w+)\]/){
    last if $guard++>50;
    my ($an,$ix)=($1,$2);
    my $iv = exists $map->{$ix} ? $map->{$ix} : ($ix=~/^-?\d+$/?$ix:undef);
    my $val=(defined $iv && $arr->{$an} && defined $arr->{$an}[$iv-1]) ? $arr->{$an}[$iv-1] : undef;
    return undef unless defined $val;
    $e =~ s/\Q$an\E\[\Q$ix\E\]/($val)/;
  }
  for my $p (sort{length($b)<=>length($a)} keys %$map){ my $v=$map->{$p}; $e=~s/\b\Q$p\E\b/($v)/g; }
  return undef if $e=~/[a-zA-Z_]/;
  return undef unless $e=~m{^[-0-9\s()+*/%.]+$};
  return eval{ no warnings; eval($e) };
}

my ($res,$un)=(0,0);
for (my $i=0;$i<@lines;$i++){
  $lines[$i] =~ s{(\w+)\[(-?\d+)\]\s+or\s+(\w+)\(([^)]*)\)}{
    my ($memo,$key,$gname,$argstr)=($1,$2,$3,$4);
    my @args=map{(my $x=$_)=~s/\s//g;$x} split/,/,$argstr;
    my $repl="$memo\[$key] or $gname(".join(",",@args).")";
    my $g=pick_gen($gname,scalar(@args),$i);
    if ($g && @args>=1){
      my %map; @map{@{$g->{params}}}=@args;
      my $val=evalexpr($g->{expr},\%map,$g->{arrays});
      if (defined $val){ $res++; $repl="$val --[[s]]"; } else { $un++; }
    } else { $un++; }
    $repl;
  }ge;
  print $lines[$i];
}
print STDERR "resolved=$res unresolved=$un gens=".scalar(@gens)."\n";
